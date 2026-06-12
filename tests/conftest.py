import subprocess
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_kubectl(monkeypatch):
    """Patch subprocess.run to intercept kubectl calls.

    Returns the mock so tests can set .return_value and inspect .call_args.
    """
    mock = MagicMock()
    mock.return_value = MagicMock(stdout="mock output", stderr="")
    monkeypatch.setattr(subprocess, "run", mock)
    return mock
