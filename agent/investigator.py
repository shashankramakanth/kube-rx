import json
import logging
import os
from datetime import datetime, timezone

from openai import OpenAI

from mcp_server.tools.cluster import k8s_list_namespaces
from mcp_server.tools.deployments import (
    k8s_deployment_diff,
    k8s_get_deployment,
    k8s_list_deployments,
    k8s_rollout_history,
    k8s_rollout_status,
)
from mcp_server.tools.nodes import (
    k8s_describe_node,
    k8s_get_node,
    k8s_get_node_conditions,
    k8s_get_node_resource_usage,
    k8s_get_pods_on_node,
    k8s_list_nodes,
)
from mcp_server.tools.pods import (
    k8s_describe_pod,
    k8s_get_container_status,
    k8s_get_pod,
    k8s_get_pod_events,
    k8s_get_pod_logs,
    k8s_get_previous_logs,
    k8s_get_restart_history,
    k8s_list_pods,
)

logger = logging.getLogger(__name__)

DIAGNOSIS_LOG = os.environ.get("DIAGNOSIS_LOG", "/var/log/kube-rx/diagnoses.log")
os.makedirs(os.path.dirname(DIAGNOSIS_LOG), exist_ok=True)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

MODEL = os.environ.get("MODEL", "deepseek/deepseek-v4-flash")
MAX_ITERATIONS = 10

SYSTEM_PROMPT = """You are a Kubernetes SRE investigating an alert.
Use the available tools to gather evidence — describe the pod, check logs, events, and restart history.
Be methodical: start with what you know from the alert, then dig deeper based on what you find.
When you have enough information to explain the root cause, respond with a clear diagnosis.
Do not call more tools once you have reached a conclusion."""

TOOL_REGISTRY = {
    # cluster
    "k8s_list_namespaces":         lambda args: k8s_list_namespaces(),
    # pods
    "k8s_list_pods":               lambda args: k8s_list_pods(**args),
    "k8s_get_pod":                 lambda args: k8s_get_pod(**args),
    "k8s_describe_pod":            lambda args: k8s_describe_pod(**args),
    "k8s_get_pod_logs":            lambda args: k8s_get_pod_logs(**args),
    "k8s_get_previous_logs":       lambda args: k8s_get_previous_logs(**args),
    "k8s_get_pod_events":          lambda args: k8s_get_pod_events(**args),
    "k8s_get_container_status":    lambda args: k8s_get_container_status(**args),
    "k8s_get_restart_history":     lambda args: k8s_get_restart_history(**args),
    # deployments
    "k8s_list_deployments":        lambda args: k8s_list_deployments(**args),
    "k8s_get_deployment":          lambda args: k8s_get_deployment(**args),
    "k8s_rollout_status":          lambda args: k8s_rollout_status(**args),
    "k8s_rollout_history":         lambda args: k8s_rollout_history(**args),
    "k8s_deployment_diff":         lambda args: k8s_deployment_diff(**args),
    # nodes
    "k8s_list_nodes":              lambda args: k8s_list_nodes(),
    "k8s_get_node":                lambda args: k8s_get_node(**args),
    "k8s_describe_node":           lambda args: k8s_describe_node(**args),
    "k8s_get_node_conditions":     lambda args: k8s_get_node_conditions(**args),
    "k8s_get_node_resource_usage": lambda args: k8s_get_node_resource_usage(**args),
    "k8s_get_pods_on_node":        lambda args: k8s_get_pods_on_node(**args),
}

TOOLS = [
    # ── cluster ───────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "k8s_list_namespaces",
            "description": "List all namespaces in the cluster. Call this first when the namespace is unknown.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    # ── pods ──────────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "k8s_list_pods",
            "description": "List all pods in a namespace. Pass 'all' for every namespace.",
            "parameters": {
                "type": "object",
                "properties": {"namespace": {"type": "string"}},
                "required": ["namespace"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "k8s_get_pod",
            "description": "Get the full YAML spec and status of a single pod.",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                    "pod_name":  {"type": "string"},
                },
                "required": ["namespace", "pod_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "k8s_describe_pod",
            "description": "Describe a pod — events, conditions, resource limits, probe status. Best first call when a pod is unhealthy.",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                    "pod_name":  {"type": "string"},
                },
                "required": ["namespace", "pod_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "k8s_get_pod_logs",
            "description": "Fetch recent logs from a running pod.",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                    "pod_name":  {"type": "string"},
                    "container": {"type": "string"},
                    "tail":      {"type": "integer"},
                },
                "required": ["namespace", "pod_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "k8s_get_previous_logs",
            "description": "Fetch logs from the previous (crashed) container instance. Use after CrashLoopBackOff.",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                    "pod_name":  {"type": "string"},
                    "container": {"type": "string"},
                },
                "required": ["namespace", "pod_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "k8s_get_pod_events",
            "description": "List Kubernetes events for a specific pod (OOMKilled, BackOff, Pulling, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                    "pod_name":  {"type": "string"},
                },
                "required": ["namespace", "pod_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "k8s_get_container_status",
            "description": "Return ready flag, restart count, current state, and last termination reason per container.",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                    "pod_name":  {"type": "string"},
                },
                "required": ["namespace", "pod_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "k8s_get_restart_history",
            "description": "Restart count and last exit code/reason for every container in a pod.",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                    "pod_name":  {"type": "string"},
                },
                "required": ["namespace", "pod_name"],
            },
        },
    },
    # ── deployments ───────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "k8s_list_deployments",
            "description": "List all deployments in a namespace with replica counts.",
            "parameters": {
                "type": "object",
                "properties": {"namespace": {"type": "string"}},
                "required": ["namespace"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "k8s_get_deployment",
            "description": "Get the full YAML spec of a deployment — image, replicas, resource limits, env vars.",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace":       {"type": "string"},
                    "deployment_name": {"type": "string"},
                },
                "required": ["namespace", "deployment_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "k8s_rollout_status",
            "description": "Check whether a rollout has completed successfully.",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace":       {"type": "string"},
                    "deployment_name": {"type": "string"},
                },
                "required": ["namespace", "deployment_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "k8s_rollout_history",
            "description": "List all recorded revisions for a deployment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace":       {"type": "string"},
                    "deployment_name": {"type": "string"},
                },
                "required": ["namespace", "deployment_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "k8s_deployment_diff",
            "description": "Show the full spec for a specific rollout revision. Call k8s_rollout_history first to find revision numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace":       {"type": "string"},
                    "deployment_name": {"type": "string"},
                    "revision":        {"type": "integer"},
                },
                "required": ["namespace", "deployment_name", "revision"],
            },
        },
    },
    # ── nodes ─────────────────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "k8s_list_nodes",
            "description": "List all nodes in the cluster with status, roles, and age.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "k8s_get_node",
            "description": "Get the full YAML spec of a node — capacity, allocatable resources, labels, taints.",
            "parameters": {
                "type": "object",
                "properties": {"node_name": {"type": "string"}},
                "required": ["node_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "k8s_describe_node",
            "description": "Describe a node — conditions, allocated resources, running pods, events.",
            "parameters": {
                "type": "object",
                "properties": {"node_name": {"type": "string"}},
                "required": ["node_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "k8s_get_node_conditions",
            "description": "Return node conditions: Ready, MemoryPressure, DiskPressure, PIDPressure, NetworkUnavailable.",
            "parameters": {
                "type": "object",
                "properties": {"node_name": {"type": "string"}},
                "required": ["node_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "k8s_get_node_resource_usage",
            "description": "Show live CPU and memory consumption for a node. Requires metrics-server.",
            "parameters": {
                "type": "object",
                "properties": {"node_name": {"type": "string"}},
                "required": ["node_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "k8s_get_pods_on_node",
            "description": "List all pods running on a specific node across all namespaces.",
            "parameters": {
                "type": "object",
                "properties": {"node_name": {"type": "string"}},
                "required": ["node_name"],
            },
        },
    },
]


def _write_diagnosis(alertname: str, namespace: str, pod: str, content: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    header = f"[{ts}] alert={alertname} namespace={namespace} pod={pod}"
    separator = "=" * 80
    entry = f"{separator}\n{header}\n{separator}\n{content}\n\n"
    try:
        with open(DIAGNOSIS_LOG, "a") as f:
            f.write(entry)
    except OSError as e:
        logger.error("failed to write diagnosis log: %s", e)


def investigate(alert: dict) -> None:
    labels      = alert.get("labels", {})
    annotations = alert.get("annotations", {})

    alertname   = labels.get("alertname", "unknown")
    namespace   = labels.get("namespace", "unknown")
    pod         = labels.get("pod", "unknown")
    severity    = labels.get("severity", "unknown")
    summary     = annotations.get("summary", "")
    description = annotations.get("description", "")

    logger.info("investigation started | alert=%s pod=%s namespace=%s", alertname, pod, namespace)

    user_message = (
        f"Alert: {alertname} (severity={severity})\n"
        f"Namespace: {namespace}\n"
        f"Pod: {pod}\n"
        f"Summary: {summary}\n"
        f"Description: {description}\n\n"
        "Please investigate and diagnose the root cause."
    )

    messages = [{"role": "user", "content": user_message}]

    for _ in range(MAX_ITERATIONS):
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        message = response.choices[0].message

        if not message.tool_calls:
            logger.info("diagnosis | alert=%s pod=%s\n%s", alertname, pod, message.content)
            _write_diagnosis(alertname, namespace, pod, message.content)
            return

        messages.append(message)

        for tool_call in message.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            logger.info("tool call | %s(%s)", name, args)

            result = TOOL_REGISTRY[name](args) if name in TOOL_REGISTRY else f"ERROR: unknown tool {name}"

            logger.debug("tool result | %s → %s", name, result[:200])

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

    logger.warning("investigation hit max iterations | alert=%s pod=%s", alertname, pod)
