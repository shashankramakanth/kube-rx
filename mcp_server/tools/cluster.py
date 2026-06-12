from mcp_server.instance import mcp
from mcp_server.kubectl import _run_kubectl


@mcp.tool()
def k8s_list_namespaces() -> str:
    """List all namespaces in the Kubernetes cluster.

    Call this first when you don't know what namespaces exist.
    Returns the raw kubectl output — namespace names.
    """
    return _run_kubectl(["get", "namespaces"])
