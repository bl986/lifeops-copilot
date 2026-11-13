"""Registry of toggleable data connectors (like connectors / data stores in Gemini Enterprise)."""

CONNECTORS = [
    {"id": "portfolio", "name": "Portfolio profile",
     "description": "Bowen's experience, certifications, education and projects (SQLite).",
     "default": True},
    {"id": "sample_data", "name": "Sample database",
     "description": "Demo expenses and tasks, queried with model-written read-only SQL.",
     "default": True},
    {"id": "project", "name": "About this project",
     "description": "How this app is built: architecture, design decisions and trade-offs, from my own notes.",
     "default": True},
    {"id": "github", "name": "GitHub (live)",
     "description": "Public repositories and latest commits, fetched live from GitHub's API.",
     "default": True},
    {"id": "gcp_docs", "name": "Google Cloud docs",
     "description": "Live passages from official Google Cloud documentation (BigQuery, Dataflow, Pub/Sub), with links.",
     "default": True},
    {"id": "google_search", "name": "Google Search grounding",
     "description": "Cited answers from the live web for Google Cloud and AI questions. -> Edit: Optional. Needs Gemini API search-grounding quota, which free keys may not include.",
     "default": False},
]

IDS = [c["id"] for c in CONNECTORS]
DEFAULTS = [c["id"] for c in CONNECTORS if c["default"]]


def resolve(requested):
    """None -> defaults. Otherwise keep only known ids, in registry order."""
    if requested is None:
        return list(DEFAULTS)
    wanted = set(requested)
    return [i for i in IDS if i in wanted]