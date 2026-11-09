import json
import urllib.error
from types import SimpleNamespace as NS

import pytest
from fastapi.testclient import TestClient

from backend import agent, connectors, github_tools, grounding, main
from backend.ratelimit import RateLimiter


# ---------- connector registry and tool wiring ----------
def test_resolve_defaults_and_unknown_ids():
    assert connectors.resolve(None) == connectors.DEFAULTS
    assert connectors.resolve([]) == []
    assert connectors.resolve(["github", "evil", "github"]) == ["github"]


def test_google_search_is_off_by_default():
    assert "google_search" not in connectors.DEFAULTS


def tool_names(enabled):
    return [t.__name__ for t in agent.build_tools([], enabled)]


def test_tools_follow_connectors():
    assert tool_names(["portfolio"]) == ["get_portfolio"]
    assert tool_names([]) == []
    assert set(tool_names(connectors.IDS)) == {
        "get_portfolio", "query_database", "get_github_activity", "search_google"}


def test_note_lists_switched_off_connectors():
    note = agent._connector_note(agent.build_tools([], ["portfolio"]))
    assert "Google Search grounding" in note
    assert "Portfolio profile" not in note


def test_followups_only_use_enabled_connectors():
    picks = agent.suggest_followups("hi", [], enabled=["github"])
    assert set(picks) <= set(agent.GITHUB_PROMPTS)
    assert agent.suggest_followups("hi", [], enabled=[]) == []


def test_chat_passes_connector_choices(monkeypatch):
    seen = {}

    def fake_run(message, enabled=None):
        seen["enabled"] = enabled
        return {"status": "success", "response": "ok", "latency": 0,
                "tools_called": [], "suggestions": [], "sources": []}

    monkeypatch.setattr(agent, "run_agent", fake_run)
    monkeypatch.setattr(main, "ip_limiter", RateLimiter(100, 60))
    client = TestClient(main.app)
    assert client.post("/chat", json={"message": "hi", "connectors": ["github"]}).status_code == 200
    assert seen["enabled"] == ["github"]
    client.post("/chat", json={"message": "hi"})
    assert seen["enabled"] is None


def test_connectors_endpoint_lists_all():
    data = TestClient(main.app).get("/connectors").json()
    assert [c["id"] for c in data["connectors"]] == connectors.IDS


# ---------- GitHub ----------
REPOS = [
    {"name": "lifeops-copilot", "description": "AI portfolio copilot", "language": "Python",
     "stargazers_count": 1, "pushed_at": "2026-11-08T10:00:00Z", "fork": False, "topics": ["fastapi"]},
    {"name": "forked-thing", "fork": True},
]
COMMITS = [{"commit": {"message": "Add rate limiting\n\nSECRETBODY",
                       "author": {"date": "2026-11-08T09:00:00Z"}}}]


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


@pytest.fixture(autouse=True)
def clear_github_cache():
    github_tools._cache.clear()


@pytest.fixture
def fake_github(monkeypatch):
    monkeypatch.setattr(github_tools, "_get_json",
                        lambda path: COMMITS if "/commits" in path else REPOS)


def test_lists_repos_without_forks(fake_github):
    out = github_tools.get_github_activity()
    assert "lifeops-copilot" in out["text"]
    assert "forked-thing" not in out["text"]
    assert out["sources"][0]["url"].startswith("https://github.com/")


def test_commits_for_a_known_repo(fake_github):
    out = github_tools.get_github_activity("lifeops-copilot")
    assert "Add rate limiting" in out["text"]
    assert "SECRETBODY" not in out["text"]  # only the first line of a commit message


def test_unknown_repo_is_rejected_without_calling_commits(monkeypatch):
    paths = []

    def fake(path):
        paths.append(path)
        return REPOS

    monkeypatch.setattr(github_tools, "_get_json", fake)
    out = github_tools.get_github_activity("../../etc/passwd")
    assert "No public repository" in out["text"]
    assert all("/commits" not in p for p in paths)


def test_responses_are_cached(monkeypatch):
    calls = []

    def fake_urlopen(request, timeout=0):
        calls.append(request.full_url)
        return FakeResponse(REPOS)

    monkeypatch.setattr(github_tools.urllib.request, "urlopen", fake_urlopen)
    github_tools.get_github_activity()
    github_tools.get_github_activity()
    assert len(calls) == 1


def test_github_failure_gives_a_friendly_message(monkeypatch):
    def boom(request, timeout=0):
        raise urllib.error.URLError("down")

    monkeypatch.setattr(github_tools.urllib.request, "urlopen", boom)
    assert "temporarily unavailable" in github_tools.get_github_activity()["text"]


# ---------- Google Search grounding ----------
def fake_response():
    chunks = [
        NS(web=NS(uri="https://example.com/a", title="Example A")),
        NS(web=NS(uri="https://example.com/a", title="duplicate")),
        NS(web=NS(uri="http://insecure.test", title="not https")),
        NS(web=None),
    ]
    return NS(text="answer", candidates=[NS(grounding_metadata=NS(grounding_chunks=chunks))])


def test_sources_are_deduped_and_https_only():
    assert grounding.extract_sources(fake_response()) == [
        {"title": "Example A", "url": "https://example.com/a"}]


def test_missing_metadata_gives_no_sources():
    assert grounding.extract_sources(NS(candidates=[])) == []
    assert grounding.extract_sources(NS(candidates=[NS(grounding_metadata=None)])) == []


def test_grounding_has_an_hourly_cap(monkeypatch):
    monkeypatch.setattr(grounding, "_limiter", RateLimiter(1, 3600))
    monkeypatch.setattr(grounding, "_generate", lambda q: fake_response())
    assert grounding.ask_google("what is dataflow prime?")["text"] == "answer"
    assert "hourly demo limit" in grounding.ask_google("again")["text"]


# ---------- agent tools ----------
def test_search_tool_records_sources(monkeypatch):
    monkeypatch.setattr(grounding, "ask_google", lambda q: {
        "text": "Dataflow Prime is a service.",
        "sources": [{"title": "Docs", "url": "https://example.com/d"}]})
    trace = []
    tools = {t.__name__: t for t in agent.build_tools(trace, ["google_search"])}
    out = tools["search_google"]("what is dataflow prime?")
    assert "Dataflow Prime" in out
    assert trace[0]["sources"][0]["url"] == "https://example.com/d"


def test_search_tool_survives_failure(monkeypatch):
    def boom(q):
        raise RuntimeError("quota")

    monkeypatch.setattr(grounding, "ask_google", boom)
    tools = {t.__name__: t for t in agent.build_tools([], ["google_search"])}
    assert "unavailable" in tools["search_google"]("x")


def test_run_agent_returns_sources_and_connectors(monkeypatch):
    source = {"title": "r", "url": "https://github.com/bl986/r"}
    monkeypatch.setattr(github_tools, "get_github_activity",
                        lambda repo="": {"text": "repos", "sources": [source]})

    def fake_model(message, tools):
        {t.__name__: t for t in tools}["get_github_activity"]()
        return "answer"

    monkeypatch.setattr(agent, "_call_model", fake_model)
    result = agent.run_agent("what has he built?")
    assert result["sources"] == [source]
    assert "github" in result["connectors"]