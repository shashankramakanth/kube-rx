# kube-rx

An AI-powered Kubernetes debugger. When something breaks in the cluster, the system detects it, investigates using MCP tools, and recommends a fix.

## Architecture

```
FastAPI app (3 pods)
       │ exposes /metrics
       ▼
  Prometheus          ← scrapes metrics every 15s
       │ alert fires
       ▼
  Alertmanager        ← defines what "broken" means
       │ webhook POST
       ▼
  AI Agent (Python)   ← Claude API + MCP tools
       │ commits fix
       ▼
    GitHub            ← source of truth
       │ detects change
       ▼
    ArgoCD            ← syncs cluster automatically
       │
       ▼
  Cluster healed ✅
```

## Layer 1 — FastAPI App

A minimal failure simulator that gives Prometheus and the AI agent something to observe and fix.

| Endpoint | Behaviour |
|---|---|
| `GET /health` | Returns `{"status": "ok"}` — used by Kubernetes liveness probe |
| `GET /metrics` | Exposes Prometheus metrics |
| `GET /stress` | Burns CPU for 30 seconds — triggers HighCPU alert |
| `GET /crash` | Kills the process with `os._exit(1)` — triggers CrashLoopBackOff |

### Repo structure

```
kube-rx/
├── app/
│   ├── main.py            # FastAPI app
│   ├── requirements.txt
│   └── Dockerfile
├── k8s/
│   ├── namespace.yaml     # healer namespace
│   ├── deployment.yaml    # 3 replicas, liveness probe on /health
│   └── service.yaml       # NodePort 30080
```

### Deploy

```bash
# On the control plane after every push
cd kube-rx && git pull && kubectl apply -f k8s/
```

### Test

```bash
curl http://<worker-node-ip>:30080/health
curl http://<worker-node-ip>:30080/metrics
curl http://<worker-node-ip>:30080/stress
curl http://<worker-node-ip>:30080/crash   # pod dies and restarts
```

### Docker image

```
docker.io/shashankramakanth/healer-app:v1.0.1
```

Built for `linux/amd64`. To rebuild and push:

```bash
docker build --platform linux/amd64 -t shashankramakanth/healer-app:<tag> ./app
docker push shashankramakanth/healer-app:<tag>
```

## Layer 2 — Prometheus Stack

Installed via `kube-prometheus-stack` Helm chart (release name `monitoring`). The operator picks up `ServiceMonitor` and `PrometheusRule` resources that carry the label `release: monitoring`.

```
kube-rx/
├── monitoring/
│   ├── servicemonitor.yaml       # tells Prometheus where to scrape the app
│   ├── prometheus-rules.yaml     # alert definitions
│   └── alertmanager-config.yaml  # webhook routing to the AI agent
```

### ServiceMonitor

Scrapes `/metrics` on the `healer-app` Service every 15 s. Targets pods in the `healer` namespace via the `http-metrics` named port.

### Alert Rules

All alerts are scoped to `namespace="healer"`.

| Alert | Expression | Threshold | For | Severity |
|---|---|---|---|---|
| `PodCrashLooping` | `increase(kube_pod_container_status_restarts_total[5m])` | > 3 restarts | 1 m | critical |
| `HighCPU` | `rate(container_cpu_usage_seconds_total[2m])` | > 0.4 cores (80% of 500 m limit) | 2 m | warning |
| `HighErrorRate` | 5xx rate / total request rate | > 5% | 1 m | critical |
| `PodNotReady` | `kube_pod_status_ready == 0` | any pod not ready | 2 m | warning |

Trigger them manually:

```bash
curl http://<worker-node-ip>:30080/stress   # → HighCPU
curl http://<worker-node-ip>:30080/crash    # → PodCrashLooping, PodNotReady
```

### Alertmanager routing

`AlertmanagerConfig` (namespace `monitoring`) matches alerts where `namespace=healer` and forwards them via webhook to the AI agent:

```
http://healer-agent.healer.svc.cluster.local:8080/webhook
```

> **Note:** The Alertmanager CR must set `alertmanagerConfigMatcherStrategy: None`. Without it, the operator injects `namespace=monitoring` as a forced matcher and healer alerts never route through.

### Deploy

```bash
kubectl apply -f monitoring/
```

## Layer 3 — MCP Tools

An MCP server wraps `kubectl` commands so the AI agent can query and act on the cluster.

### Repo structure

```
kube-rx/
└── mcp_server/
    ├── instance.py       # shared FastMCP instance
    ├── kubectl.py        # _run_kubectl helper
    ├── server.py         # entry point — registers tools, runs server
    └── tools/
        ├── cluster.py    # cluster-scoped tools
        ├── nodes.py      # node tools
        ├── pods.py       # pod tools
        └── deployments.py # deployment tools
```

### Tools

**Cluster**

| Tool | Description |
|---|---|
| `k8s_list_namespaces()` | Lists all namespaces. Call this first when the namespace is unknown. |

**Nodes**

| Tool | Description |
|---|---|
| `k8s_list_nodes()` | All nodes with status, roles, and age. |
| `k8s_get_node(node_name)` | Full YAML spec — capacity, allocatable resources, labels, taints. |
| `k8s_describe_node(node_name)` | Conditions, allocated resources, running pods, events. Best first call when a node is unhealthy. |
| `k8s_get_node_conditions(node_name)` | Focused view of node conditions (Ready, MemoryPressure, DiskPressure, PIDPressure, NetworkUnavailable). |
| `k8s_get_node_resource_usage(node_name)` | Live CPU and memory consumption. Requires metrics-server. |
| `k8s_get_pods_on_node(node_name)` | All pods running on a node across all namespaces. Use to assess blast radius. |

**Pods**

| Tool | Description |
|---|---|
| `k8s_list_pods(namespace)` | Lists pods in a namespace. Pass `"all"` for every namespace. |
| `k8s_get_pod(namespace, pod_name)` | Full YAML spec and status of a single pod. |
| `k8s_describe_pod(namespace, pod_name)` | Events, conditions, resource limits, probe status. Best first call when a pod is unhealthy. |
| `k8s_get_pod_logs(namespace, pod_name, container?, tail?)` | Recent logs from a running container. `tail` defaults to 100 lines. |
| `k8s_get_previous_logs(namespace, pod_name, container?)` | Logs from the previous (crashed) container instance. Use after CrashLoopBackOff. |
| `k8s_get_pod_events(namespace, pod_name)` | Kubernetes events scoped to a pod (OOMKilled, BackOff, Pulling, etc.), sorted by time. |
| `k8s_get_container_status(namespace, pod_name)` | Ready flag, restart count, current state, and last termination reason per container. |
| `k8s_get_restart_history(namespace, pod_name)` | Restart count + last exit code and reason. Useful for diagnosing crash loops. |

**Deployments**

| Tool | Description |
|---|---|
| `k8s_list_deployments(namespace)` | All deployments with desired, ready, up-to-date, and available replica counts. |
| `k8s_get_deployment(namespace, deployment_name)` | Full YAML spec — image, replicas, resource limits, env vars, update strategy. |
| `k8s_rollout_status(namespace, deployment_name)` | Whether a rollout has completed. Use after a deploy or restart. |
| `k8s_rollout_history(namespace, deployment_name)` | All recorded revisions. Call first to discover revision numbers. |
| `k8s_rollout_restart(namespace, deployment_name)` | Triggers a rolling restart of all pods. **Mutating.** |
| `k8s_rollback_deployment(namespace, deployment_name, revision?)` | Rolls back to a previous revision. Omit `revision` to undo the last rollout. **Mutating.** |
| `k8s_deployment_diff(namespace, deployment_name, revision)` | Full spec for a specific revision. Call for two revisions to compare what changed. |

### Run locally

```bash
export KUBECONFIG=~/.kube/kube-rx.yaml
python mcp_server/server.py                          # stdio (default)
python mcp_server/server.py --transport sse --port 8080  # SSE
```

### Test a tool manually

```bash
KUBECONFIG=~/.kube/kube-rx.yaml .venv/bin/python -c "from mcp_server.tools.pods import k8s_list_pods; print(k8s_list_pods('healer'))"
```

### Run tests

```bash
.venv/bin/python -m pytest tests/ -v
```

In production, `KUBECONFIG` is injected via a pod service account or Secrets Manager — no credentials file needed.
