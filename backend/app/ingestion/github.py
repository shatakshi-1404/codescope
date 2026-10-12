import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from app.core.errors import InvalidBranchError, InvalidRepositoryURLError

_OWNER_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
_REPO_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
# Must start with a letter/digit, so a value like "--upload-pack=..." can never pass.
_BRANCH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$")
_ALLOWED_HOSTS = {"github.com", "www.github.com"}

_HINT = "Enter a valid GitHub repository URL, e.g. https://github.com/owner/repository"


@dataclass(frozen=True)
class GitHubRepoRef:
    owner: str
    repo: str

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.repo}"

    @property
    def normalized_url(self) -> str:
        # GitHub is case-insensitive, so lowercase makes duplicate detection reliable.
        return f"https://github.com/{self.owner}/{self.repo}".lower()


def parse_github_url(raw: str) -> GitHubRepoRef:
    text = (raw or "").strip()
    if not text or len(text) > 300 or any(ch.isspace() or ord(ch) < 32 for ch in text):
        raise InvalidRepositoryURLError(_HINT)

    if "://" not in text:
        text = "https://" + text

    try:
        parts = urlsplit(text)
        port = parts.port
    except ValueError:
        raise InvalidRepositoryURLError(_HINT) from None

    if parts.scheme not in ("http", "https"):
        raise InvalidRepositoryURLError("The URL must start with https://")
    if parts.username or parts.password or port:
        raise InvalidRepositoryURLError("The URL must not contain credentials or a port.")
    if (parts.hostname or "").lower() not in _ALLOWED_HOSTS:
        raise InvalidRepositoryURLError("Only public github.com repositories are supported.")

    segments = [s for s in parts.path.split("/") if s]
    if len(segments) < 2:
        raise InvalidRepositoryURLError(_HINT)

    owner = segments[0]
    repo = segments[1].removesuffix(".git")
    if not _OWNER_RE.match(owner) or not _REPO_RE.match(repo) or repo in (".", ".."):
        raise InvalidRepositoryURLError(_HINT)

    return GitHubRepoRef(owner=owner, repo=repo)


def validate_branch(branch: str) -> str:
    b = (branch or "").strip()
    if (
        not _BRANCH_RE.match(b)
        or ".." in b
        or "//" in b
        or b.endswith(("/", ".", ".lock"))
    ):
        raise InvalidBranchError("That is not a valid branch or tag name.")
    return b
