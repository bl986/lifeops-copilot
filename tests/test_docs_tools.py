import pytest

from backend import agent, docs_tools


def page_html(sentence):
    return "<html><body><nav>NAVJUNK navigation words that must not appear</nav><main>" + \
        "".join(f"<p>{sentence} (paragraph {i})</p>" for i in range(12)) + \
        "</main><script>var ignored = 1;</script></body></html>"


SENTENCES = {
    "bigquery-intro": "BigQuery is a fully managed data warehouse for analytics over large datasets",
    "bigquery-analytics": "BigQuery runs SQL queries and supports machine learning with BigQuery ML models",
    "dataflow": "Dataflow runs Apache Beam pipelines for streaming and batch data processing",
    "pubsub": "Pub/Sub is an asynchronous messaging service that decouples publishers and subscribers",
}
HTML_BY_URL = {p["url"]: page_html(SENTENCES[p["id"]]) for p in docs_tools.PAGES}


@pytest.fixture(autouse=True)
def reset_state():
    docs_tools._cache.clear()
    docs_tools._failed.clear()


@pytest.fixture
def fake_pages(monkeypatch):
    calls = []

    def fake_fetch(url):
        calls.append(url)
        return HTML_BY_URL[url]

    monkeypatch.setattr(docs_tools, "_fetch_html", fake_fetch)
    return calls


def test_allowlist_is_https_and_on_google_hosts():
    for page in docs_tools.PAGES:
        assert page["url"].startswith("https://")
        assert page["url"].split("/")[2] in docs_tools.ALLOWED_HOSTS


def test_html_to_text_drops_navigation_and_scripts():
    out = docs_tools.html_to_text(page_html("Some real documentation content that is long enough"))
    assert "NAVJUNK" not in out and "ignored" not in out
    assert "real documentation content" in out


def test_question_finds_the_right_page(fake_pages):
    result = docs_tools.search_docs("Why is Pub/Sub described as asynchronous messaging?")
    assert result["sources"][0]["title"] == "Pub/Sub overview"
    assert result["sources"][0]["url"].startswith("https://docs.cloud.google.com/")
    assert result["top_score"] > 0
    assert "asynchronous" in result["text"]


def test_off_topic_question_returns_no_passages(fake_pages):
    result = docs_tools.search_docs("chocolate cake recipe with frosting")
    assert result["text"].startswith("NO_RELEVANT_PASSAGES")
    assert result["sources"] == []


def test_pages_are_cached(fake_pages):
    docs_tools.search_docs("What is Dataflow?")
    docs_tools.search_docs("What is BigQuery?")
    assert len(fake_pages) == len(docs_tools.PAGES)


def test_fetch_failure_gives_friendly_message(monkeypatch):
    def boom(url):
        raise OSError("network down")

    monkeypatch.setattr(docs_tools, "_fetch_html", boom)
    assert "temporarily unavailable" in docs_tools.search_docs("What is Dataflow?")["text"]


def test_redirect_outside_allowlist_is_rejected(monkeypatch):
    class Resp:
        def geturl(self):
            return "https://evil.example/page"

        def read(self, n=-1):
            return b"<html></html>"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(docs_tools.urllib.request, "urlopen", lambda req, timeout=0: Resp())
    with pytest.raises(ValueError):
        docs_tools._fetch_html(docs_tools.PAGES[0]["url"])


def test_agent_tool_records_sources_and_score(monkeypatch):
    monkeypatch.setattr(docs_tools, "search_docs", lambda q: {
        "text": "Source: Pub/Sub overview", "top_score": 5.0,
        "sources": [{"title": "Pub/Sub overview", "url": "https://docs.cloud.google.com/pubsub/docs/overview"}]})
    trace = []
    tools = {t.__name__: t for t in agent.build_tools(trace, ["gcp_docs"])}
    assert "Pub/Sub" in tools["search_gcp_docs"]("what is pub/sub?")
    assert trace[0]["sources"][0]["title"] == "Pub/Sub overview"
    assert trace[0]["top_score"] == 5.0