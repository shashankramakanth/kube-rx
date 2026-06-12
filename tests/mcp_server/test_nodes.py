from mcp_server.tools.nodes import (
    k8s_describe_node,
    k8s_get_node,
    k8s_get_node_conditions,
    k8s_get_node_resource_usage,
    k8s_get_pods_on_node,
    k8s_list_nodes,
)


def kubectl_args(mock):
    return mock.call_args[0][0]


class TestListNodes:
    def test_command(self, mock_kubectl):
        k8s_list_nodes()
        assert kubectl_args(mock_kubectl) == ["kubectl", "get", "nodes", "-o", "wide"]


class TestGetNode:
    def test_command(self, mock_kubectl):
        k8s_get_node("worker-1")
        assert kubectl_args(mock_kubectl) == ["kubectl", "get", "node", "worker-1", "-o", "yaml"]


class TestDescribeNode:
    def test_command(self, mock_kubectl):
        k8s_describe_node("worker-1")
        assert kubectl_args(mock_kubectl) == ["kubectl", "describe", "node", "worker-1"]


class TestGetNodeConditions:
    def test_command(self, mock_kubectl):
        k8s_get_node_conditions("worker-1")
        args = kubectl_args(mock_kubectl)
        assert "worker-1" in args
        assert any("conditions" in a for a in args)


class TestGetNodeResourceUsage:
    def test_command(self, mock_kubectl):
        k8s_get_node_resource_usage("worker-1")
        assert kubectl_args(mock_kubectl) == ["kubectl", "top", "node", "worker-1"]


class TestGetPodsOnNode:
    def test_command(self, mock_kubectl):
        k8s_get_pods_on_node("worker-1")
        args = kubectl_args(mock_kubectl)
        assert "-A" in args
        assert "--field-selector=spec.nodeName=worker-1" in args
