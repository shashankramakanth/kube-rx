from mcp_server.tools.cluster import k8s_list_namespaces


def kubectl_args(mock):
    return mock.call_args[0][0]


class TestListNamespaces:
    def test_command(self, mock_kubectl):
        k8s_list_namespaces()
        assert kubectl_args(mock_kubectl) == ["kubectl", "get", "namespaces"]
