import subprocess


def _run_kubectl(kubectl_args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["kubectl", *kubectl_args],
            capture_output=True, text=True, timeout=15,
        )
    except FileNotFoundError:
        return "ERROR: kubectl not found on PATH."
    return result.stdout or result.stderr
