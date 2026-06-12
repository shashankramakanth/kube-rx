from mcp_server.instance import mcp
from mcp_server.kubectl import _run_kubectl


@mcp.tool()
def k8s_list_nodes() -> str:
    """List all nodes in the cluster with status, roles, and age.

    Use this to get an overview of cluster capacity and spot nodes that are
    NotReady or have scheduling disabled.
    """
    return _run_kubectl(["get", "nodes", "-o", "wide"])


@mcp.tool()
def k8s_get_node(node_name: str) -> str:
    """Get the full YAML spec of a node.

    Returns capacity, allocatable resources, labels, taints, and conditions.
    Useful for understanding what a node offers and why pods may not schedule on it.
    """
    return _run_kubectl(["get", "node", node_name, "-o", "yaml"])


@mcp.tool()
def k8s_describe_node(node_name: str) -> str:
    """Describe a node — conditions, allocated resources, running pods, and events.

    Best first tool when a node is unhealthy. Shows CPU/memory pressure,
    disk pressure, and which pods are consuming resources.
    """
    return _run_kubectl(["describe", "node", node_name])


@mcp.tool()
def k8s_get_node_conditions(node_name: str) -> str:
    """Return just the conditions array for a node.

    Conditions: Ready, MemoryPressure, DiskPressure, PIDPressure, NetworkUnavailable.
    Faster than describe when you only need to check node health status.
    """
    return _run_kubectl([
        "get", "node", node_name,
        "-o", "jsonpath={range .status.conditions[*]}"
                       "type={.type}  status={.status}  reason={.reason}  message={.message}\\n{end}",
    ])


@mcp.tool()
def k8s_get_node_resource_usage(node_name: str) -> str:
    """Show live CPU and memory consumption for a node.

    Returns actual usage (not requests/limits) in cores and bytes.
    Requires metrics-server to be installed in the cluster.
    """
    return _run_kubectl(["top", "node", node_name])


@mcp.tool()
def k8s_get_pods_on_node(node_name: str) -> str:
    """List all pods running on a specific node across all namespaces.

    Use this to assess blast radius when a node is unhealthy — shows
    which workloads are affected.
    """
    return _run_kubectl([
        "get", "pods", "-A",
        f"--field-selector=spec.nodeName={node_name}",
    ])
