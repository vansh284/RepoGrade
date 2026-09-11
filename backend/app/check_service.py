import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CheckOutput:
    passed: bool
    message: str
    details: str
    stderr: str


def discover_checks(checks_directory: str) -> list[str]:
    checks_path = Path(checks_directory)
    if not checks_path.is_dir():
        return []
    return sorted(str(p) for p in checks_path.glob("*.py"))


def run_check(script_path: str, cwd: str, env: dict[str, str]) -> CheckOutput:
    import os

    full_env = {**os.environ, **env}
    try:
        result = subprocess.run(
            ["python", script_path],
            cwd=cwd,
            env=full_env,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return CheckOutput(
            passed=False,
            message="Check timed out after 120s",
            details="",
            stderr="",
        )

    stderr = result.stderr

    if result.returncode != 0:
        return CheckOutput(
            passed=False,
            message=f"Script exited with code {result.returncode}",
            details=result.stdout,
            stderr=stderr,
        )

    try:
        data = json.loads(result.stdout)
        return CheckOutput(
            passed=bool(data.get("passed", False)),
            message=str(data.get("message", "")),
            details=str(data.get("details", "")),
            stderr=stderr,
        )
    except (json.JSONDecodeError, AttributeError):
        return CheckOutput(
            passed=False,
            message="Invalid JSON output from check script",
            details=result.stdout,
            stderr=stderr,
        )
