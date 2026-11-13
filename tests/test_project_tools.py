import pytest

from backend import agent, project_tools


@pytest.fixture
def passages(tmp_path):
    (tmp_path / "design.md").write_text(
        "# Design decisions\n\n"
        "## Why SQLite\nSQLite needs no separate server and the demo data is small and read-mostly.\n\n"
        "## Why FastAPI\nFastAPI validates input with Pydantic and serves a built-in test page.\n",
        encoding="utf-8")
    (tmp_path / "arch.md").write_text(
        "# Architecture\n\n## Request flow\nThe browser posts to the chat endpoint, which calls the agent, which calls the tools.\n",
        encoding="utf-8")
    return project_tools.load_passages(tmp_path)


def test_notes_are_split_by_heading(passages):
    titles = [p["title"] for p in passages]
    assert "Design decisions: Why SQLite" in titles
    assert "Architecture: Request flow" in titles
    assert all(p["url"].startswith("https://github.com/") for p in passages)


def test_ranking_finds_the_right_section(passages):
    result = project_tools.search_notes("Why use SQLite?", passages=passages, min_score=0.0)
    assert result["sources"][0]["title"] == "Design decisions"
    assert "Why SQLite" in result["text"]
    assert result["top_score"] > 0


def test_off_topic_question_returns_no_notes():
    result = project_tools.search_notes("chocolate cake recipe with frosting")
    assert result["text"].startswith("NO_RELEVANT_NOTES")
    assert result["sources"] == []


def test_real_notes_answer_the_headline_questions():
    sqlite = project_tools.search_notes("Why does this project use SQLite?")
    assert "Why SQLite" in sqlite["text"]
    arch = project_tools.search_notes("What is the architecture of this project?")
    assert arch["sources"][0]["title"] == "Architecture"


def test_every_note_file_has_sections():
    files = list(project_tools.NOTES_DIR.glob("*.md"))
    assert len(files) >= 5
    for f in files:
        assert "\n## " in f.read_text(encoding="utf-8-sig"), f.name


def test_agent_tool_records_sources(monkeypatch):
    monkeypatch.setattr(project_tools, "search_notes", lambda q: {
        "text": "Source: Architecture: Overview", "top_score": 4.0,
        "sources": [{"title": "Architecture: Overview", "url": "https://github.com/bl986/lifeops-copilot/blob/main/backend/project_notes/architecture.md"}]})
    trace = []
    tools = {t.__name__: t for t in agent.build_tools(trace, ["project"])}
    assert "Architecture" in tools["search_project_notes"]("what is the architecture?")
    assert trace[0]["sources"][0]["title"] == "Architecture: Overview"
    assert trace[0]["top_score"] == 4.0

def test_weak_matches_are_dropped(passages):
    result = project_tools.search_notes("Why use SQLite?", passages=passages, min_score=0.0)
    assert "Why SQLite" in result["text"]
    assert "Why FastAPI" not in result["text"]

def test_generic_words_are_ignored_but_not_when_they_are_all_there_is():
    assert "project" not in project_tools._clean_question("Why does this project use SQLite?").lower()
    assert project_tools._clean_question("this project") == "this project"