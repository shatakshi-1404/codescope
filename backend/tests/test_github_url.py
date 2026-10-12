import pytest

from app.core.errors import InvalidBranchError, InvalidRepositoryURLError
from app.ingestion.github import parse_github_url, validate_branch


@pytest.mark.parametrize(
    "raw",
    [
        "https://github.com/Pallets/Click",
        "https://github.com/pallets/click.git",
        "https://github.com/pallets/click/",
        "https://www.github.com/pallets/click/tree/main/src",
        "github.com/pallets/click",
        "  https://github.com/pallets/click  ",
    ],
)
def test_valid_urls_normalize_to_one_form(raw):
    ref = parse_github_url(raw)
    assert ref.normalized_url == "https://github.com/pallets/click"


def test_full_name_keeps_original_case():
    assert parse_github_url("https://github.com/Pallets/Click").full_name == "Pallets/Click"


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "https://gitlab.com/a/b",
        "https://github.com.evil.com/a/b",
        "https://evil.com/github.com/a/b",
        "https://user:pw@github.com/a/b",
        "https://github.com:8443/a/b",
        "https://github.com/onlyowner",
        "file:///etc/passwd",
        "ssh://git@github.com/a/b",
        "git@github.com:a/b.git",
        "https://github.com/a/b c",
        "https://github.com/a/..",
    ],
)
def test_invalid_urls_are_rejected(raw):
    with pytest.raises(InvalidRepositoryURLError):
        parse_github_url(raw)


@pytest.mark.parametrize("branch", ["main", "feature/login-1", "v1.2.0", "release_2024"])
def test_valid_branches(branch):
    assert validate_branch(branch) == branch


@pytest.mark.parametrize(
    "branch", ["", "  ", "-rf", "--upload-pack=evil", "a..b", "a b", "x/", "x.lock", "a;b", "a$(id)"]
)
def test_invalid_branches_are_rejected(branch):
    with pytest.raises(InvalidBranchError):
        validate_branch(branch)
