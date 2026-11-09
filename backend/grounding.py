"""Google Search grounding, wrapped as a separate model call so it works as a tool."""
import os

from backend.ratelimit import RateLimiter

MODEL = os.environ.get("GROUNDING_MODEL", os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite"))
MAX_SOURCES = 5
INSTRUCTION = (
    "Answer the question using Google Search results. Be accurate and concise (under 200 words). "
    "Focus on Google Cloud and AI products when relevant. "
    "If the search results do not answer it, say so."
)

# Protects the free quota (separate from the per-IP limits in main.py).
_limiter = RateLimiter(int(os.environ.get("GROUNDING_MAX_PER_HOUR", "30")), 3600)


def extract_sources(response) -> list:
    """Pull unique https source links out of the grounding metadata."""
    try:
        metadata = response.candidates[0].grounding_metadata
        chunks = (metadata.grounding_chunks if metadata else None) or []
    except (AttributeError, IndexError, TypeError):
        return []
    sources, seen = [], set()
    for chunk in chunks:
        web = getattr(chunk, "web", None)
        uri = getattr(web, "uri", None) if web else None
        if not uri or uri in seen or not uri.startswith("https://"):
            continue
        seen.add(uri)
        title = (getattr(web, "title", None) or uri)[:100]
        sources.append({"title": title, "url": uri})
    return sources[:MAX_SOURCES]


def _generate(question: str):
    """The network call (replaced by a stub in tests)."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    return client.models.generate_content(
        model=MODEL,
        contents=question,
        config=types.GenerateContentConfig(
            system_instruction=INSTRUCTION,
            tools=[types.Tool(google_search=types.GoogleSearch())],
            max_output_tokens=800,
            temperature=0.2,
        ),
    )


def ask_google(question: str) -> dict:
    """Return {"text": ..., "sources": [...]}."""
    if _limiter.check("grounding"):
        return {"text": "Google Search grounding has reached its hourly demo limit. Please try again later.",
                "sources": []}
    response = _generate(question[:500])
    return {"text": (response.text or "").strip(), "sources": extract_sources(response)}