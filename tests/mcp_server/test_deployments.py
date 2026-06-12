from mcp_server.tools.deployments import (
    k8s_deployment_diff,
    k8s_get_deployment,
    k8s_list_deployments,
    k8s_rollback_deployment,
    k8s_rollout_history,
    k8s_rollout_restart,
    k8s_rollout_status,
)


def kubectl_args(mock):
    return mock.call_args[0][0]


class TestListDeployments:
    def test_command(self, mock_kubectl):
        k8s_list_deployments("healer")
        assert kubectl_args(mock_kubectl) == ["kubectl", "get", "deployments", "-n", "healer"]


class TestGetDeployment:
    def test_command(self, mock_kubectl):
        k8s_get_deployment("healer", "healer-app")
        assert kubectl_args(mock_kubectl) == [
            "kubectl", "get", "deployment", "healer-app", "-n", "healer", "-o", "yaml",
        ]


class TestRolloutStatus:
    def test_command(self, mock_kubectl):
        k8s_rollout_status("healer", "healer-app")
        assert kubectl_args(mock_kubectl) == [
            "kubectl", "rollout", "status", "deployment/healer-app", "-n", "healer",
        ]


class TestRolloutHistory:
    def test_command(self, mock_kubectl):
        k8s_rollout_history("healer", "healer-app")
        assert kubectl_args(mock_kubectl) == [
            "kubectl", "rollout", "history", "deployment/healer-app", "-n", "healer",
        ]


class TestRolloutRestart:
    def test_command(self, mock_kubectl):
        k8s_rollout_restart("healer", "healer-app")
        assert kubectl_args(mock_kubectl) == [
            "kubectl", "rollout", "restart", "deployment/healer-app", "-n", "healer",
        ]


class TestRollbackDeployment:
    def test_default_revision(self, mock_kubectl):
        k8s_rollback_deployment("healer", "healer-app")
        assert kubectl_args(mock_kubectl) == [
            "kubectl", "rollout", "undo", "deployment/healer-app", "-n", "healer",
        ]

    def test_specific_revision(self, mock_kubectl):
        k8s_rollback_deployment("healer", "healer-app", revision=3)
        assert "--to-revision=3" in kubectl_args(mock_kubectl)

    def test_no_revision_flag_when_default(self, mock_kubectl):
        k8s_rollback_deployment("healer", "healer-app")
        assert not any("to-revision" in a for a in kubectl_args(mock_kubectl))


class TestDeploymentDiff:
    def test_command(self, mock_kubectl):
        k8s_deployment_diff("healer", "healer-app", revision=2)
        args = kubectl_args(mock_kubectl)
        assert "history" in args
        assert "deployment/healer-app" in args
        assert "--revision=2" in args
