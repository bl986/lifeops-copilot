"""Live GitHub data for the agent: public repos and recent commits (read-only, cached)."""
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request

USER = os.environ.get("GITHUB_USER", "bl986")
API = "https://api.github.com"
CACHE_SECONDS = 600
TIMEOUT_SECONDS = 8
MAX_REPOS = 12
MAX_COMMITS = 5
UNAVAILABLE = "GitHub data is temporarily unavailable."

_cache = {}
_lock = threading.Lock()
_REPO_NAME = re.compile(r"^[A-Za-z0-9._-]{1,100}$")


def _get_json(path: str):
    """GET from GitHub with a small TTL cache; serves stale data if GitHub fails."""
    now = time.monotonic()
    with _lock:
        cached = _cache.get(path)
    if cached and now - cached[0] < CACHE_SECONDS:
        return cached[1]

    headers = {"Accept": "application/vnd.github+json", "User-Agent": "lifeops-copilot"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        request = urllib.request.Request(API + path, headers=headers)
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"GitHub request failed for {path}: {e}")
        if cached:
            return cached[1]  # stale data beats no data
        raise
    with _lock:
        _cache[path] = (time.monotonic(), data)
    return data


def _day(iso) -> str:
    return (iso or "")[:10] or "unknown"


def _repos() -> list:
    data = _get_json(f"/users/{USER}/repos?sort=pushed&per_page=30")
    return [r for r in data if not r.get("fork")]


def get_github_activity(repo: str = "") -> dict:
    """Return {"text": ..., "sources": [...]}. Never raises."""
    try:
        repos = _repos()
        by_name = {r["name"].lower(): r for r in repos}
        repo = (repo or "").strip()

        if not repo:
            lines = [f"Public GitHub repositories of {USER} (live data, most recently pushed first):"]
            for r in repos[:MAX_REPOS]:
                bits = [r.get("language"), f"updated {_day(r.get('pushed_at'))}"]
                if r.get("stargazers_count"):
                    bits.append(f"{r['stargazers_count']} stars")
                topics = r.get("topics") or []
                if topics:
                    bits.append("topics: " + ", ".join(topics[:5]))
                details = "; ".join(b for b in bits if b)
                lines.append(f"- {r['name']}: {r.get('description') or 'no description'} ({details})")
            sources = [{"title": f"github.com/{USER}", "url": f"https://github.com/{USER}"}]
            return {"text": "\n".join(lines), "sources": sources}

        # A repo name must match one of the user's own public repos (no arbitrary paths).
        if not _REPO_NAME.match(repo) or repo.lower() not in by_name:
            names = ", ".join(r["name"] for r in repos[:MAX_REPOS])
            return {"text": f"No public repository named '{repo[:60]}'. Available: {names}", "sources": []}

        name = by_name[repo.lower()]["name"]
        commits = _get_json(f"/repos/{USER}/{name}/commits?per_page={MAX_COMMITS}")
        lines = [f"Latest commits on {name} (live data):"]
        for c in commits[:MAX_COMMITS]:
            info = c.get("commit") or {}
            message = (info.get("message") or "").splitlines()
            first_line = message[0][:120] if message else ""
            lines.append(f"- {_day((info.get('author') or {}).get('date'))}: {first_line}")
        sources = [{"title": f"{name} on GitHub", "url": f"https://github.com/{USER}/{name}"}]
        return {"text": "\n".join(lines), "sources": sources}
    except Exception:
        return {"text": UNAVAILABLE, "sources": []}