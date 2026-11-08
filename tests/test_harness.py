from backend.harness import AgentHarness


def test_success_path():
    result = AgentHarness("test").execute("hi", lambda: "hello")
    assert result["status"] == "success"
    assert result["response"] == "hello"
    assert result["latency_seconds"] >= 0


def test_empty_response_is_flagged_as_error():
    result = AgentHarness("test").execute("hi", lambda: "   ")
    assert result["status"] == "error"
    assert "empty response" in result["response"].lower()


def test_exceptions_are_intercepted():
    def boom():
        raise RuntimeError("model exploded")

    result = AgentHarness("test").execute("hi", boom)
    assert result["status"] == "error"