"""Retrieval over the project's own design notes (backend/project_notes/*.md)."""
import os
import re
from functools import lru_cache
from pathlib import Path

from backend import docs_tools

NOTES_DIR = Path(__file__).resolve().parent / "project_notes"
REPO_URL = os.environ.get("PROJECT_REPO_URL", "https://github.com/bl986/lifeops-copilot")
NOTES_URL = REPO_URL + "/blob/main/backend/project_notes/"
# Starting guess: check "top_score" in the API response for real questions and tune.
MIN_SCORE = float(os.environ.get("PROJECT_MIN_SCORE", "1.0"))
UNAVAILABLE = "The project notes are temporarily unavailable."
_GENERIC = re.compile(r"\b(project|app|application|lifeops|copilot)\b", re.IGNORECASE)


def _clean_question(question: str) -> str:
    """Drop words that appear everywhere in these notes, so they don't skew the ranking."""
    cleaned = _GENERIC.sub(" ", question)
    return cleaned if docs_tools._tokens(cleaned) else question


def load_passages(directory: Path = NOTES_DIR) -> list:
    """One passage per '##' section of every note."""
    passages = []
    for path in sorted(Path(directory).glob("*.md")):
        title, heading, lines, sections = path.stem, "Overview", [], []
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
            elif line.startswith("## "):
                sections.append((heading, lines))
                heading, lines = line[3:].strip(), []
            else:
                lines.append(line)
        sections.append((heading, lines))
        for section, body_lines in sections:
            body = "\n".join(body_lines).strip()
            if body:
                passages.append({
                    "title": f"{title}: {section}",
                    "url": NOTES_URL + path.name,
                    "text": f"{title}: {section}\n{body}",
                })
    return passages


@lru_cache(maxsize=1)
def _default_passages() -> list:
    return load_passages()


def search_notes(question: str, min_score: float = None, passages: list = None) -> dict:
    """Return {"text", "sources", "top_score"}. Never raises."""
    min_score = MIN_SCORE if min_score is None else min_score
    try:
        passages = _default_passages() if passages is None else passages
        if not passages:
            return {"text": UNAVAILABLE, "sources": [], "top_score": 0}
        hits = docs_tools.rank(_clean_question(question), passages, k=4, min_score=min_score)
    except Exception as e:
        print(f"search_notes error: {e}")
        return {"text": UNAVAILABLE, "sources": [], "top_score": 0}

    if not hits:
        return {"text": "NO_RELEVANT_NOTES: the project notes do not cover this question.",
                "sources": [], "top_score": 0}

    top = hits[0]["score"]
    hits = [h for h in hits if h["score"] >= 0.7 * top]

    sources, seen = [], set()
    for h in hits:
        if h["url"] not in seen:
            seen.add(h["url"])
            sources.append({"title": h["title"].split(":")[0], "url": h["url"]})
    text = "\n\n---\n\n".join(f"Source: {h['title']}\n{h['text'][:2500]}" for h in hits)
    return {"text": text, "sources": sources, "top_score": hits[0]["score"]}