"""
MCP server wrapping kubectl commands for the kube-rx cluster.

Run:
    export KUBECONFIG=~/.kube/kube-rx.yaml
    python mcp_server/k8s_server.py

In production, KUBECONFIG is injected by the platform (Secrets Manager,
pod service account, CI secret). No credentials file needed.
"""

import argparse
import os
import subprocess

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("kube-rx")


def _run_kubectl(kubectl_args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["kubectl", *kubectl_args],
            capture_output=True, text=True, timeout=15,
        )
    except FileNotFoundError:
        return "ERROR: kubectl not found on PATH."
    return result.stdout or result.stderr


# ── List Pods (tool #1) ────────────────────────────────────────────────────
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


# ── List Namespaces   (tool #2) ────────────────────────────────────────────────────
@mcp.tool()
def k8s_list_namespaces() -> str:
    """List all namespaces in the Kubernetes cluster.
    Call this first when you don't know what namespaces exist.
    Returns the raw kubectl output — namespace names.
    """
    return _run_kubectl(["get", "namespaces"])


# ── Entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="kube-rx MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport protocol (stdio for Claude/pi, sse for web clients)",
    )
    parser.add_argument("--port", type=int, default=8080, help="Port for SSE transport")
    args = parser.parse_args()

    if args.transport == "sse":
        mcp.run(transport="sse", port=args.port)
    else:
        mcp.run(transport="stdio")