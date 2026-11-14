import json

import pytest
from fastapi.testclient import TestClient

from backend import connectors, github_tools, main, mcp_server, project_tools, workflows
from backend.ratelimit import RateLimiter

GH_SOURCE = {"title": "github.com/bl986", "url": "https://github.com/bl986"}
NOTE_SOURCE = {
    "title": "Architecture",
    "url": "https://github.com/bl986/lifeops-copilot/blob/main/backend/project_notes/architecture.md",
}


@pytest.fixture
def fake_data(monkeypatch):
    monkeypatch.setattr(mcp_server, "get_portfolio", lambda: "Bowen Lu (he/him), based in Canada.")
    monkeypatch.setattr(
        github_tools, "get_github_activity",
        lambda repo="": {"text": f"data for {repo or 'all repos'}", "sources": [GH_SOURCE]})
    monkeypatch.setattr(
        project_tools, "search_notes",
        lambda q: {"text": f"Source: Architecture: Overview\nnote about {q.split()[0]}",
                   "sources": [NOTE_SOURCE], "top_score": 3})


def run(workflow_id, enabled=None, summarize=None):
    enabled = connectors.IDS if enabled is None else enabled
    return list(workflows.run(workflow_id, enabled, summarize or (lambda prompt: "SUMMARY")))


def test_profile_brief_runs_steps_in_order(fake_data):
    events = run("profile_brief")
    steps = [(e["id"], e["status"]) for e in events if e["event"] == "step"]
    assert steps == [("profile", "running"), ("profile", "done"),
                     ("github", "running"), ("github", "done"),
                     ("summary", "running"), ("summary", "done")]
    assert events[0]["event"] == "start"
    result = events[-1]
    assert result["event"] == "result" and result["status"] == "success"
    assert result["response"] == "SUMMARY"
    assert result["sources"] == [GH_SOURCE]


def test_summary_prompt_contains_the_gathered_data(fake_data):
    seen = []
    run("profile_brief", summarize=lambda p: seen.append(p) or "ok")
    assert "he/him" in seen[0]
    assert "data for all repos" in seen[0]


def test_deep_dive_uses_notes_and_latest_commits(fake_data):
    seen = []
    events = run("project_deep_dive", summarize=lambda p: seen.append(p) or "ok")
    assert "note about architecture" in seen[0]
    assert "note about design" in seen[0]
    assert "data for lifeops-copilot" in seen[0]
    assert events[-1]["sources"] == [NOTE_SOURCE, GH_SOURCE]


def test_blocked_when_a_required_connector_is_off(fake_data):
    called = []
    events = run("profile_brief", enabled=["portfolio"], summarize=lambda p: called.append(p) or "x")
    result = events[-1]
    assert result["status"] == "blocked"
    assert "GitHub (live)" in result["response"]
    assert called == []
    assert not [e for e in events if e["event"] == "step"]


def test_github_outage_is_skipped_with_a_warning(fake_data, monkeypatch):
    monkeypatch.setattr(github_tools, "get_github_activity",
                        lambda repo="": {"text": "GitHub data is temporarily unavailable.", "sources": []})
    seen = []
    events = run("profile_brief", summarize=lambda p: seen.append(p) or "ok")
    final = {e["id"]: e["status"] for e in events if e["event"] == "step"}
    assert final["github"] == "warning"
    assert "UNAVAILABLE" in seen[0]
    assert events[-1]["status"] == "success"


def test_required_step_failure_stops_the_workflow(fake_data, monkeypatch):
    def boom():
        raise RuntimeError("db down")

    monkeypatch.setattr(mcp_server, "get_portfolio", boom)
    called = []
    events = run("profile_brief", summarize=lambda p: called.append(p) or "x")
    assert events[-1]["status"] == "error"
    assert "db down" not in events[-1]["response"]
    assert called == []


def test_summary_failure_gives_a_generic_message(fake_data):
    def boom(prompt):
        raise RuntimeError("secret detail")

    result = run("profile_brief", summarize=boom)[-1]
    assert result["status"] == "error"
    assert "secret detail" not in result["response"]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "ip_limiter", RateLimiter(100, 60))
    monkeypatch.setattr(main, "global_limiter", RateLimiter(100, 60))
    return TestClient(main.app)


def test_workflows_endpoint_lists_both(client):
    data = client.get("/workflows").json()["workflows"]
    assert [w["id"] for w in data] == ["profile_brief", "project_deep_dive"]
    assert data[0]["steps"][-1] == "Write the summary"


def test_workflow_endpoint_streams_json_lines(client, fake_data, monkeypatch):
    monkeypatch.setattr(workflows, "_summarize", lambda prompt: "SUMMARY")
    response = client.post("/workflow", json={"workflow": "profile_brief"})
    assert response.status_code == 200
    events = [json.loads(line) for line in response.text.splitlines() if line]
    assert events[0]["event"] == "start"
    assert events[-1]["event"] == "result" and events[-1]["status"] == "success"


def test_unknown_workflow_is_404(client):
    assert client.post("/workflow", json={"workflow": "nope"}).status_code == 404


def test_workflow_endpoint_is_rate_limited(monkeypatch):
    monkeypatch.setattr(main, "ip_limiter", RateLimiter(1, 60))
    monkeypatch.setattr(main, "global_limiter", RateLimiter(100, 60))
    monkeypatch.setattr(workflows, "run", lambda wid, enabled: iter(
        [{"event": "result", "status": "success", "response": "ok", "sources": []}]))
    client = TestClient(main.app)
    assert client.post("/workflow", json={"workflow": "profile_brief"}).status_code == 200
    blocked = client.post("/workflow", json={"workflow": "profile_brief"})
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers

def test_success_result_includes_followup_suggestions(fake_data):
    result = run("profile_brief")[-1]
    assert 1 <= len(result["suggestions"]) <= 3

def test_exactly_one_result_event(fake_data):
    events = run("profile_brief")
    assert len([e for e in events if e["event"] == "result"]) == 1