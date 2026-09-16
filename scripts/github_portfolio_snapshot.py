#!/usr/bin/env python3
"""Fetch a compact snapshot of public repositories from the GitHub REST API.

This is intentionally dependency-free. By default it reads DMDTague's public
repositories, but GITHUB_USER can point it at any public GitHub account.
If GITHUB_TOKEN is set, the request is authenticated and receives the normal
higher GitHub API rate limit.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_VERSION = "2022-11-28"
DEFAULT_USER = "DMDTague"
OUTPUT = Path(__file__).resolve().parents[1] / "data" / "github_snapshot.json"


def request_json(url: str) -> object:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
        "User-Agent": "DMDTague-profile-snapshot",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=20) as response:
            return json.load(response)
    except HTTPError as exc:
        raise SystemExit(f"GitHub API returned HTTP {exc.code}: {exc.reason}") from exc
    except URLError as exc:
        raise SystemExit(f"Could not reach GitHub API: {exc.reason}") from exc


def fetch_public_repositories(username: str) -> list[dict[str, object]]:
    url = (
        f"https://api.github.com/users/{username}/repos"
        "?type=owner&sort=updated&direction=desc&per_page=100"
    )
    payload = request_json(url)
    if not isinstance(payload, list):
        raise SystemExit("Unexpected GitHub API response: expected a repository list")

    repositories: list[dict[str, object]] = []
    for repo in payload:
        if not isinstance(repo, dict) or repo.get("fork"):
            continue
        repositories.append(
            {
                "name": repo.get("name"),
                "url": repo.get("html_url"),
                "description": repo.get("description"),
                "language": repo.get("language"),
                "stars": repo.get("stargazers_count", 0),
                "forks": repo.get("forks_count", 0),
                "open_issues": repo.get("open_issues_count", 0),
                "updated_at": repo.get("updated_at"),
            }
        )
    return repositories


def main() -> None:
    username = os.getenv("GITHUB_USER", DEFAULT_USER)
    repositories = fetch_public_repositories(username)
    snapshot = {
        "source": "GitHub REST API",
        "username": username,
        "repository_count": len(repositories),
        "total_stars": sum(int(repo["stars"]) for repo in repositories),
        "repositories": repositories,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(repositories)} repositories to {OUTPUT}")


if __name__ == "__main__":
    main()
