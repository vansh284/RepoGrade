import subprocess
from pathlib import Path


def clone_repo(url: str, dest: str) -> None:
    subprocess.run(
        ["git", "clone", url, dest],
        check=True,
        capture_output=True,
        text=True,
    )


def repo_exists(dest: str) -> bool:
    return Path(dest).joinpath(".git").is_dir()
