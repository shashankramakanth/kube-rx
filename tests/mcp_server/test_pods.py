import subprocess
from unittest.mock import MagicMock

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


def kubectl_args(mock):
    return mock.call_args[0][0]


class TestListPods:
    def test_specific_namespace(self, mock_kubectl):
        k8s_list_pods("healer")
        assert kubectl_args(mock_kubectl) == ["kubectl", "get", "pods", "-n", "healer"]

    def test_all_namespaces(self, mock_kubectl):
        k8s_list_pods("all")
        assert kubectl_args(mock_kubectl) == ["kubectl", "get", "pods", "-A"]

    def test_all_namespaces_flag(self, mock_kubectl):
        k8s_list_pods("-A")
        assert kubectl_args(mock_kubectl) == ["kubectl", "get", "pods", "-A"]

    def test_returns_stdout(self, mock_kubectl):
        mock_kubectl.return_value = MagicMock(stdout="pod-a   Running", stderr="")
        assert k8s_list_pods("healer") == "pod-a   Running"


class TestGetPod:
    def test_command(self, mock_kubectl):
        k8s_get_pod("healer", "healer-app-abc123")
        assert kubectl_args(mock_kubectl) == [
            "kubectl", "get", "pod", "healer-app-abc123", "-n", "healer", "-o", "yaml",
        ]


class TestDescribePod:
    def test_command(self, mock_kubectl):
        k8s_describe_pod("healer", "healer-app-abc123")
        assert kubectl_args(mock_kubectl) == [
            "kubectl", "describe", "pod", "healer-app-abc123", "-n", "healer",
        ]


class TestGetPodLogs:
    def test_default_tail(self, mock_kubectl):
        k8s_get_pod_logs("healer", "healer-app-abc123")
        assert kubectl_args(mock_kubectl) == [
            "kubectl", "logs", "healer-app-abc123", "-n", "healer", "--tail=100",
        ]

    def test_custom_tail(self, mock_kubectl):
        k8s_get_pod_logs("healer", "healer-app-abc123", tail=50)
        assert "--tail=50" in kubectl_args(mock_kubectl)

    def test_with_container(self, mock_kubectl):
        k8s_get_pod_logs("healer", "healer-app-abc123", container="healer-app")
        args = kubectl_args(mock_kubectl)
        assert "-c" in args
        assert "healer-app" in args

    def test_without_container_no_c_flag(self, mock_kubectl):
        k8s_get_pod_logs("healer", "healer-app-abc123")
        assert "-c" not in kubectl_args(mock_kubectl)


class TestGetPreviousLogs:
    def test_includes_previous_flag(self, mock_kubectl):
        k8s_get_previous_logs("healer", "healer-app-abc123")
        assert "--previous" in kubectl_args(mock_kubectl)

    def test_with_container(self, mock_kubectl):
        k8s_get_previous_logs("healer", "healer-app-abc123", container="healer-app")
        args = kubectl_args(mock_kubectl)
        assert "-c" in args
        assert "healer-app" in args

    def test_without_container_no_c_flag(self, mock_kubectl):
        k8s_get_previous_logs("healer", "healer-app-abc123")
        assert "-c" not in kubectl_args(mock_kubectl)


class TestGetPodEvents:
    def test_command(self, mock_kubectl):
        k8s_get_pod_events("healer", "healer-app-abc123")
        args = kubectl_args(mock_kubectl)
        assert "events" in args
        assert "--field-selector=involvedObject.name=healer-app-abc123" in args
        assert "--sort-by=.lastTimestamp" in args


class TestGetContainerStatus:
    def test_command(self, mock_kubectl):
        k8s_get_container_status("healer", "healer-app-abc123")
        args = kubectl_args(mock_kubectl)
        assert "healer-app-abc123" in args
        assert any("containerStatuses" in a for a in args)


class TestGetRestartHistory:
    def test_command(self, mock_kubectl):
        k8s_get_restart_history("healer", "healer-app-abc123")
        args = kubectl_args(mock_kubectl)
        assert "healer-app-abc123" in args
        assert any("restartCount" in a for a in args)


class TestRunKubectlErrors:
    def test_kubectl_not_found(self, monkeypatch):
        monkeypatch.setattr(subprocess, "run", MagicMock(side_effect=FileNotFoundError))
        result = k8s_list_pods("healer")
        assert "ERROR" in result
        assert "kubectl" in result

    def test_returns_stderr_when_no_stdout(self, mock_kubectl):
        mock_kubectl.return_value = MagicMock(stdout="", stderr="Error from server: not found")
        result = k8s_get_pod("healer", "missing-pod")
        assert "Error from server" in result
