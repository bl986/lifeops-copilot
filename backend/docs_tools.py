"""Live retrieval over a fixed allowlist of official Google Cloud documentation pages.

Pages are fetched on demand (cached), split into passages and ranked against the
question with a BM25-style keyword score. Visitors never supply URLs.
Documentation content: Google, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/).
"""
import math
import os
import re
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from urllib.parse import urlparse

PAGES = [
    {"id": "bigquery-intro", "title": "BigQuery overview",
     "url": "https://docs.cloud.google.com/bigquery/docs/introduction"},
    {"id": "bigquery-analytics", "title": "Overview of BigQuery analytics",
     "url": "https://docs.cloud.google.com/bigquery/docs/query-overview"},
    {"id": "dataflow", "title": "Dataflow overview",
     "url": "https://docs.cloud.google.com/dataflow/docs/overview"},
    {"id": "pubsub", "title": "Pub/Sub overview",
     "url": "https://docs.cloud.google.com/pubsub/docs/overview"},
]
ALLOWED_HOSTS = {"docs.cloud.google.com", "cloud.google.com"}
CACHE_SECONDS = 6 * 3600
RETRY_AFTER_FAILURE = 60
TIMEOUT_SECONDS = 8
MAX_BYTES = 2_000_000
CHUNK_CHARS = 900
TOP_K = 4
# Starting guess: check "top_score" in the API response for real questions and tune.
MIN_SCORE = float(os.environ.get("DOCS_MIN_SCORE", "2.0"))
UNAVAILABLE = "The documentation connector is temporarily unavailable."

_cache = {}      # page id -> (fetched_at, passages)
_failed = {}     # page id -> time of last failure
_lock = threading.Lock()

STOPWORDS = set(
    "a an and are as at be by can do does for from how i in is it its of on or "
    "that the this to was what when where which who why with you your my me".split()
)


# ---------- HTML to text ----------
class _TextExtractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "nav", "header", "footer", "aside", "svg", "form", "button"}
    BREAK = {"p", "li", "h1", "h2", "h3", "h4", "div", "section", "article", "tr", "br", "pre", "td", "th"}

    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif tag in self.BREAK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip = max(0, self.skip - 1)
        elif tag in self.BREAK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    lines = (re.sub(r"\s+", " ", line).strip() for line in "".join(parser.parts).split("\n"))
    return "\n".join(line for line in lines if len(line) >= 20)


def to_passages(page: dict, text: str) -> list:
    chunks, current = [], ""
    for line in text.split("\n"):
        if current and len(current) + len(line) > CHUNK_CHARS:
            chunks.append(current)
            current = ""
        current = (current + " " + line).strip()
    if current:
        chunks.append(current)
    return [{"title": page["title"], "url": page["url"], "text": c} for c in chunks]


# ---------- Fetching ----------
def _fetch_html(url: str) -> str:
    """Download one allowlisted page (replaced by a stub in tests)."""
    request = urllib.request.Request(
        url, headers={"User-Agent": "lifeops-copilot", "Accept": "text/html"}
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        final = urlparse(response.geturl())
        if final.scheme != "https" or final.hostname not in ALLOWED_HOSTS:
            raise ValueError(f"redirected outside the allowlist: {final.hostname}")
        return response.read(MAX_BYTES).decode("utf-8", errors="replace")


def _safe_load(page: dict) -> list:
    try:
        text = html_to_text(_fetch_html(page["url"]))
        if len(text) < 500:
            raise ValueError("page text too short; extraction probably failed")
        return to_passages(page, text)
    except Exception as e:
        print(f"docs fetch failed for {page['id']}: {e}")
        return []


def load_passages() -> list:
    """All cached passages; refreshes stale pages in parallel and keeps old data if a refresh fails."""
    now = time.monotonic()
    with _lock:
        stale = []
        for page in PAGES:
            fetched = _cache.get(page["id"])
            if fetched and now - fetched[0] < CACHE_SECONDS:
                continue
            failed_at = _failed.get(page["id"])
            if failed_at is not None and now - failed_at < RETRY_AFTER_FAILURE:
                continue
            stale.append(page)
    if stale:
        with ThreadPoolExecutor(max_workers=len(stale)) as pool:
            results = list(pool.map(_safe_load, stale))
        with _lock:
            for page, passages in zip(stale, results):
                if passages:
                    _cache[page["id"]] = (time.monotonic(), passages)
                    _failed.pop(page["id"], None)
                else:
                    _failed[page["id"]] = time.monotonic()
    with _lock:
        return [p for page in PAGES for p in _cache.get(page["id"], (0, []))[1]]


# ---------- Ranking (BM25-style) ----------
def _tokens(text: str) -> list:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 1 and t not in STOPWORDS]


def rank(question: str, passages: list, k: int = TOP_K, min_score: float = MIN_SCORE) -> list:
    query = set(_tokens(question))
    if not query or not passages:
        return []
    docs = [_tokens(p["text"]) for p in passages]
    n = len(docs)
    avg_len = sum(len(d) for d in docs) / n or 1.0
    df = {}
    for d in docs:
        for t in set(d):
            df[t] = df.get(t, 0) + 1

    k1, b = 1.5, 0.75
    scored = []
    for passage, d in zip(passages, docs):
        tf = {}
        for t in d:
            tf[t] = tf.get(t, 0) + 1
        score = 0.0
        for t in query:
            f = tf.get(t, 0)
            if not f:
                continue
            idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
            score += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * len(d) / avg_len))
        scored.append((score, passage))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [{**p, "score": round(s, 2)} for s, p in scored[:k] if s >= min_score]


# ---------- Public entry point ----------
def search_docs(question: str, min_score: float = None) -> dict:
    """Return {"text", "sources", "top_score"}. Never raises."""
    min_score = MIN_SCORE if min_score is None else min_score
    try:
        passages = load_passages()
        if not passages:
            return {"text": UNAVAILABLE, "sources": [], "top_score": 0}
        hits = rank(question, passages, min_score=min_score)
    except Exception as e:
        print(f"search_docs error: {e}")
        return {"text": UNAVAILABLE, "sources": [], "top_score": 0}

    if not hits:
        covered = ", ".join(p["title"] for p in PAGES)
        return {"text": f"NO_RELEVANT_PASSAGES: the pages in this connector ({covered}) do not cover this question.",
                "sources": [], "top_score": 0}

    sources, seen = [], set()
    for h in hits:
        if h["url"] not in seen:
            seen.add(h["url"])
            sources.append({"title": h["title"], "url": h["url"]})
    text = "\n\n---\n\n".join(
        f"Source: {h['title']} ({h['url']})\n{h['text'][:1200]}" for h in hits
    )
    return {"text": text, "sources": sources, "top_score": hits[0]["score"]}