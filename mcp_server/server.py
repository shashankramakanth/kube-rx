"""
MCP server wrapping kubectl commands for the kube-rx cluster.

Run:
    export KUBECONFIG=~/.kube/kube-rx.yaml
    python mcp_server/server.py

In production, KUBECONFIG is injected by the platform (Secrets Manager,
pod service account, CI secret). No credentials file needed.
"""

import argparse

from mcp_server.instance import mcp
import mcp_server.tools.cluster      # registers cluster-scoped tools as side effect
import mcp_server.tools.nodes        # registers node tools as side effect
import mcp_server.tools.pods         # registers pod tools as side effect
import mcp_server.tools.deployments  # registers deployment tools as side effect

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="kube-rx MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport protocol (stdio for Claude, sse for web clients)",
    )
    parser.add_argument("--port", type=int, default=8080, help="Port for SSE transport")
    args = parser.parse_args()

    if args.transport == "sse":
        mcp.run(transport="sse", port=args.port)
    else:
        mcp.run(transport="stdio")
