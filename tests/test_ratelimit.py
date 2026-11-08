from fastapi.testclient import TestClient

from backend import agent, main
from backend.ratelimit import RateLimiter


def test_blocks_after_limit_and_recovers():
    limiter = RateLimiter(2, 60)
    assert limiter.check("a", now=0) == 0
    assert limiter.check("a", now=1) == 0
    assert limiter.check("a", now=2) > 0
    assert limiter.check("b", now=2) == 0   # other clients are unaffected
    assert limiter.check("a", now=61) == 0  # window has slid past the first hit


def _fake_agent(monkeypatch):
    monkeypatch.setattr(
        agent, "run_agent",
        lambda m: {"status": "success", "response": "ok", "latency": 0, "tools_called": []},
    )


def test_chat_endpoint_is_rate_limited(monkeypatch):
    _fake_agent(monkeypatch)
    monkeypatch.setattr(main, "ip_limiter", RateLimiter(2, 60))
    client = TestClient(main.app)
    assert client.post("/chat", json={"message": "hi"}).status_code == 200
    assert client.post("/chat", json={"message": "hi"}).status_code == 200
    blocked = client.post("/chat", json={"message": "hi"})
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers
    assert "too quickly" in blocked.json()["response"]


def test_chat_rejects_bad_input(monkeypatch):
    _fake_agent(monkeypatch)
    monkeypatch.setattr(main, "ip_limiter", RateLimiter(100, 60))
    client = TestClient(main.app)
    assert client.post("/chat", json={"message": ""}).status_code == 422
    assert client.post("/chat", json={"message": "x" * 501}).status_code == 422