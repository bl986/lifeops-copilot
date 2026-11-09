"""Registry of toggleable data connectors (like connectors / data stores in Gemini Enterprise)."""

CONNECTORS = [
    {"id": "portfolio", "name": "Portfolio profile",
     "description": "Bowen's experience, certifications, education and projects (SQLite).",
     "default": True},
    {"id": "sample_data", "name": "Sample database",
     "description": "Demo expenses and tasks, queried with model-written read-only SQL.",
     "default": True},
    {"id": "github", "name": "GitHub (live)",
     "description": "Public repositories and latest commits, fetched live from GitHub's API.",
     "default": True},
    {"id": "google_search", "name": "Google Search grounding",
     "description": "Cited answers from the live web for Google Cloud and AI questions.",
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