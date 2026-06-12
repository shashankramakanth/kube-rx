from mcp_server.instance import mcp
from mcp_server.kubectl import _run_kubectl


@mcp.tool()
def k8s_list_deployments(namespace: str) -> str:
    """List all deployments in a namespace with replica counts and age.

    Shows desired, ready, up-to-date, and available replica counts — useful
    for spotting a stuck or partially-rolled-out deployment at a glance.
    """
    return _run_kubectl(["get", "deployments", "-n", namespace])


@mcp.tool()
def k8s_get_deployment(namespace: str, deployment_name: str) -> str:
    """Get the full YAML spec of a deployment.

    Returns the complete spec including image, replicas, resource limits,
    environment variables, volume mounts, and update strategy.
    """
    return _run_kubectl(["get", "deployment", deployment_name, "-n", namespace, "-o", "yaml"])


@mcp.tool()
def k8s_rollout_status(namespace: str, deployment_name: str) -> str:
    """Check whether a rollout has completed successfully.

    Blocks until the rollout finishes or reports the current progress.
    Use this after a deploy or restart to confirm all replicas are ready.
    """
    return _run_kubectl(["rollout", "status", f"deployment/{deployment_name}", "-n", namespace])


@mcp.tool()
def k8s_rollout_history(namespace: str, deployment_name: str) -> str:
    """List all recorded revisions for a deployment.

    Shows revision numbers and the change cause annotation. Call this first
    to discover available revisions before fetching a specific revision's diff.
    """
    return _run_kubectl(["rollout", "history", f"deployment/{deployment_name}", "-n", namespace])


@mcp.tool()
def k8s_rollout_restart(namespace: str, deployment_name: str) -> str:
    """Trigger a rolling restart of all pods in a deployment.

    Patches the deployment with a restart annotation so pods are replaced
    one by one using the existing update strategy. Mutating — use when pods
    are stuck or need to pick up a new ConfigMap/Secret value.
    """
    return _run_kubectl(["rollout", "restart", f"deployment/{deployment_name}", "-n", namespace])


@mcp.tool()
def k8s_rollback_deployment(namespace: str, deployment_name: str, revision: int = 0) -> str:
    """Roll a deployment back to a previous revision.

    Args:
        namespace: Namespace the deployment lives in.
        deployment_name: Name of the deployment.
        revision: Revision number to roll back to (from rollout_history).
                  Defaults to 0, which rolls back to the immediately previous revision.

    Mutating — this replaces the live deployment spec.
    """
    args = ["rollout", "undo", f"deployment/{deployment_name}", "-n", namespace]
    if revision:
        args.append(f"--to-revision={revision}")
    return _run_kubectl(args)


@mcp.tool()
def k8s_deployment_diff(namespace: str, deployment_name: str, revision: int) -> str:
    """Show the full spec for a specific rollout revision.

    Call k8s_rollout_history first to find revision numbers, then call this
    for each revision you want to compare. Useful for spotting what changed
    (image tag, env vars, resource limits) between a working and broken revision.
    """
    return _run_kubectl([
        "rollout", "history", f"deployment/{deployment_name}",
        "-n", namespace,
        f"--revision={revision}",
    ])
