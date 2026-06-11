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
