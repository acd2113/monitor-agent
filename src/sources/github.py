import re

import httpx

from src.config import settings
from src.models import SourceItem, ToolOutput
from src.sources.base import parse_date, strip_html

GITHUB_API_URL = "https://api.github.com"


def repo_from_url(url):
    if not url:
        return None, None

    match = re.search(r"github\.com/([^/?#]+)/([^/?#]+)", url)
    if not match:
        return None, None

    owner = match.group(1)
    repo = match.group(2).rstrip("/")
    if owner in {"orgs", "topics", "search", "sponsors"}:
        return None, None
    return owner, repo


def _headers():
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "MonitorAgent/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.github_api_key:
        headers["Authorization"] = f"Bearer {settings.github_api_key}"
    return headers


def _request(path, params=None):
    response = httpx.get(
        GITHUB_API_URL + path,
        params=params,
        headers=_headers(),
        timeout=settings.request_timeout,
    )
    response.raise_for_status()
    return response.json()


def _release_item(owner, repo, row):
    title = row.get("name") or row.get("tag_name") or "GitHub Release"
    body = strip_html(row.get("body") or "")
    published_at, published_missing = parse_date(
        row.get("published_at") or row.get("created_at")
    )
    url = row.get("html_url") or f"https://github.com/{owner}/{repo}"
    return SourceItem(
        title=f"{owner}/{repo}: {title}",
        url=url,
        source=f"github:{owner}/{repo}",
        published_at=published_at,
        published_missing=published_missing,
        snippet=body[:500],
        content=body[:1000],
        tier=3,
        guid=f"gh-release:{row.get('id') or row.get('tag_name') or url}",
    )


def _commit_item(owner, repo, row):
    commit = row.get("commit", {}) if isinstance(row, dict) else {}
    message = commit.get("message", "") or ""
    title = message.splitlines()[0] if message else "GitHub Commit"
    body = strip_html(message)
    published_at, published_missing = parse_date(
        (commit.get("committer") or {}).get("date")
        or (commit.get("author") or {}).get("date")
    )
    url = row.get("html_url") or f"https://github.com/{owner}/{repo}"
    return SourceItem(
        title=f"{owner}/{repo}: {title}",
        url=url,
        source=f"github:{owner}/{repo}",
        published_at=published_at,
        published_missing=published_missing,
        snippet=body[:500],
        content=body[:1000],
        tier=4,
        guid=f"gh-commit:{row.get('sha') or url}",
    )


def fetch_github(url, max_releases=5, max_commits=5):
    owner, repo = repo_from_url(url)
    if not owner or not repo:
        return ToolOutput(text=f"Invalid GitHub repository URL: {url}", items=[])

    try:
        releases = _request(
            f"/repos/{owner}/{repo}/releases",
            params={"per_page": max_releases},
        )
        commits = _request(
            f"/repos/{owner}/{repo}/commits",
            params={"per_page": max_commits},
        )
    except Exception as exc:
        return ToolOutput(text=f"GitHub fetch failed for {owner}/{repo}: {exc}", items=[])

    if not isinstance(releases, list):
        releases = []
    if not isinstance(commits, list):
        commits = []

    items = []
    for row in releases[:max_releases]:
        items.append(_release_item(owner, repo, row))
    for row in commits[:max_commits]:
        items.append(_commit_item(owner, repo, row))

    if not items:
        return ToolOutput(text=f"No releases or commits found for {owner}/{repo}.", items=[])

    lines = [f"{item.title}\n{item.url}\n{item.snippet}" for item in items]
    return ToolOutput(text="\n\n".join(lines), items=items)
