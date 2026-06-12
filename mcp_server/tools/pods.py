from mcp_server.instance import mcp
from mcp_server.kubectl import _run_kubectl


@mcp.tool()
def k8s_list_pods(namespace: str) -> str:
    """List all pods in a Kubernetes namespace.

    Use 'all' (or '-A') to list pods across every namespace.
    Use a specific namespace name (e.g. 'healer', 'default') to filter.

    Returns the raw kubectl output — pod names, status, restarts, and age.
    """
    args = ["get", "pods"]
    if namespace.lower() in ("all", "-a", "-A"):
        args.append("-A")
    else:
        args.extend(["-n", namespace])
    return _run_kubectl(args)


@mcp.tool()
def k8s_get_pod(namespace: str, pod_name: str) -> str:
    """Get the full YAML spec and status of a single pod.

    Returns the raw kubectl output in YAML format including spec, status,
    conditions, and container details.
    """
    return _run_kubectl(["get", "pod", pod_name, "-n", namespace, "-o", "yaml"])


@mcp.tool()
def k8s_describe_pod(namespace: str, pod_name: str) -> str:
    """Describe a pod — events, conditions, resource requests/limits, probe status.

    Best first tool to call when a pod is unhealthy. Returns the full
    kubectl describe output.
    """
    return _run_kubectl(["describe", "pod", pod_name, "-n", namespace])


@mcp.tool()
def k8s_get_pod_logs(namespace: str, pod_name: str, container: str = "", tail: int = 100) -> str:
    """Fetch recent logs from a running pod.

    Args:
        namespace: Namespace the pod lives in.
        pod_name: Name of the pod.
        container: Container name (required for multi-container pods; leave empty for single-container pods).
        tail: Number of lines to return from the end of the log (default 100).
    """
    args = ["logs", pod_name, "-n", namespace, f"--tail={tail}"]
    if container:
        args.extend(["-c", container])
    return _run_kubectl(args)


@mcp.tool()
def k8s_get_previous_logs(namespace: str, pod_name: str, container: str = "") -> str:
    """Fetch logs from the previous (crashed) container instance.

    Use this after a CrashLoopBackOff to see what the container printed
    before it died.

    Args:
        namespace: Namespace the pod lives in.
        pod_name: Name of the pod.
        container: Container name (leave empty for single-container pods).
    """
    args = ["logs", pod_name, "-n", namespace, "--previous"]
    if container:
        args.extend(["-c", container])
    return _run_kubectl(args)


@mcp.tool()
def k8s_get_pod_events(namespace: str, pod_name: str) -> str:
    """List Kubernetes events for a specific pod.

    Returns Warning and Normal events (OOMKilled, BackOff, Pulling, etc.)
    scoped to the named pod.
    """
    return _run_kubectl([
        "get", "events", "-n", namespace,
        f"--field-selector=involvedObject.name={pod_name}",
        "--sort-by=.lastTimestamp",
    ])


@mcp.tool()
def k8s_get_container_status(namespace: str, pod_name: str) -> str:
    """Return the containerStatuses array for a pod.

    Shows state (running/waiting/terminated), ready flag, restart count,
    and last termination reason for each container.
    """
    return _run_kubectl([
        "get", "pod", pod_name, "-n", namespace,
        "-o", "jsonpath={range .status.containerStatuses[*]}"
                       "{.name}\\t{.ready}\\t{.restartCount}\\t{.state}\\t{.lastState}\\n{end}",
    ])


@mcp.tool()
def k8s_get_restart_history(namespace: str, pod_name: str) -> str:
    """Return restart counts and last termination reason for every container in a pod.

    Useful for diagnosing crash loops — shows exit code and reason from
    the last terminated state alongside the cumulative restart count.
    """
    return _run_kubectl([
        "get", "pod", pod_name, "-n", namespace,
        "-o", "jsonpath={range .status.containerStatuses[*]}"
                       "container={.name}  restarts={.restartCount}"
                       "  lastExitCode={.lastState.terminated.exitCode}"
                       "  lastReason={.lastState.terminated.reason}\\n{end}",
    ])
