import os
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.core.errors import (
    AppError,
    InvalidBranchError,
    RepositoryCloneError,
    RepositoryNotFoundError,
)

CLONE_TIMEOUT_SECONDS = 120
LS_REMOTE_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class ClonedRepo:
    path: Path
    branch: str
    commit_sha: str


def _git_env(home: str) -> dict[str, str]:
    """A minimal, locked-down environment. The server's own env/secrets are NOT passed to git."""
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": home,                      # keeps git away from any user-level config
        "LC_ALL": "C",                     # predictable error messages
        "GIT_TERMINAL_PROMPT": "0",        # never hang waiting for a username/password
        "GIT_ALLOW_PROTOCOL": "https",     # no file://, ssh://, git:// ...
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_LFS_SKIP_SMUDGE": "1",
    }


def _map_git_error(stderr: str, branch: str | None) -> AppError:
    text = stderr.lower()
    if "remote branch" in text and "not found" in text:
        return InvalidBranchError(f"Branch or tag '{branch}' was not found in this repository.")
    if any(
        s in text
        for s in ("not found", "could not read username", "authentication failed", "terminal prompts disabled")
    ):
        return RepositoryNotFoundError(
            "Repository not found, or it is private. CodeScope can only analyze public repositories."
        )
    return RepositoryCloneError("Could not download the repository from GitHub. Please try again.")


def _run_git(
    args: list[str], *, timeout: int, branch: str | None = None, cwd: str | None = None
) -> str:
    # List arguments, no shell: user input can never become a shell command.
    cmd = ["git", "-c", "core.symlinks=false", "-c", "core.hooksPath=/dev/null", *args]
    with tempfile.TemporaryDirectory(prefix="codescope-home-") as home:
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=timeout,
                cwd=cwd,
                env=_git_env(home),
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise RepositoryCloneError(
                "Timed out while downloading the repository. It may be too large."
            ) from None
        except FileNotFoundError:
            raise RepositoryCloneError("git is not installed on the server.") from None

    if proc.returncode != 0:
        raise _map_git_error(proc.stderr, branch)
    return proc.stdout


def fetch_default_branch(url: str) -> str:
    """Cheap existence check + default branch lookup, without downloading any code."""
    out = _run_git(["ls-remote", "--symref", "--", url, "HEAD"], timeout=LS_REMOTE_TIMEOUT_SECONDS)
    for line in out.splitlines():
        if line.startswith("ref:"):
            ref = line.split()[1]
            return ref.removeprefix("refs/heads/")
    raise RepositoryCloneError("This repository appears to be empty.")


def _dir_size(path: str) -> int:
    total = 0
    for dirpath, _dirs, files in os.walk(path, followlinks=False):
        for name in files:
            try:
                total += os.lstat(os.path.join(dirpath, name)).st_size
            except OSError:
                pass
    return total


@contextmanager
def clone_repository(url: str, branch: str | None) -> Iterator[ClonedRepo]:
    """
    Shallow-clones into a temporary folder and yields it.
    The folder is deleted when the `with` block ends, on success OR on error.
    """
    with tempfile.TemporaryDirectory(prefix="codescope-clone-") as workdir:
        dest = os.path.join(workdir, "repo")

        args = ["clone", "--depth", "1", "--single-branch", "--no-tags"]
        if branch:
            args += ["--branch", branch]
        args += ["--", url, dest]
        _run_git(args, timeout=CLONE_TIMEOUT_SECONDS, branch=branch)

        if _dir_size(dest) > settings.max_repo_mb * 1024 * 1024:
            raise RepositoryCloneError(
                f"This repository is too large to analyze (limit: {settings.max_repo_mb} MB)."
            )

        commit = _run_git(["rev-parse", "HEAD"], timeout=15, cwd=dest).strip()
        current = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], timeout=15, cwd=dest).strip()
        # Cloning a tag leaves a detached HEAD; fall back to the name that was asked for.
        resolved = branch if (current == "HEAD" and branch) else current

        yield ClonedRepo(path=Path(dest), branch=resolved, commit_sha=commit)
