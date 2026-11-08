import os

import pytest

from backend import agent


def test_tool_calls_are_traced(monkeypatch):
    def fake_model(message, tools):
        by_name = {t.__name__: t for t in tools}
        by_name["get_portfolio"]()
        return "Here you go"

    monkeypatch.setattr(agent, "_call_model", fake_model)
    result = agent.run_agent("Tell me about Bowen")
    assert result["status"] == "success"
    assert result["response"] == "Here you go"
    assert [c["tool"] for c in result["tools_called"]] == ["get_portfolio"]


def test_model_failure_returns_generic_message(monkeypatch):
    def broken(message, tools):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(agent, "_call_model", broken)
    result = agent.run_agent("hi")
    assert result["status"] == "error"
    assert result["response"] == agent.GENERIC_ERROR
    assert "secret internal detail" not in result["response"]


needs_key = pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"), reason="live eval needs GEMINI_API_KEY"
)


@needs_key
@pytest.mark.parametrize("question,expected_tool", [
    ("What tasks are pending?", "query_database"),
    ("How much did I spend on groceries?", "query_database"),
    ("Where did Bowen study?", "get_portfolio"),
])
def test_tool_selection_eval(question, expected_tool):
    """Live eval: does the real model pick the right tool? Skipped in CI (no key)."""
    result = agent.run_agent(question)
    assert result["status"] == "success"
    assert expected_tool in [c["tool"] for c in result["tools_called"]]