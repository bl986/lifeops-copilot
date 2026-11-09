"""SQLite data layer: schema, seed data, and a guarded read-only query runner."""
import os
import re
import sqlite3
from contextlib import closing
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "lifeops.db"
MAX_ROWS = 50

SCHEMA = """
CREATE TABLE IF NOT EXISTS portfolio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL COLLATE NOCASE,
    title TEXT NOT NULL,
    description TEXT,
    link TEXT
);
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    category TEXT NOT NULL COLLATE NOCASE,
    amount REAL NOT NULL,
    description TEXT
);
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task TEXT NOT NULL,
    status TEXT NOT NULL COLLATE NOCASE,
    due_date TEXT
);
"""

# Shown to the LLM so it can write correct SQL.
SCHEMA_DESCRIPTION = """Tables:
portfolio(id, category, title, description, link)  -- category is Experience, Skills, Certification, Education or Project
expenses(id, date, category, amount, description)  -- date is YYYY-MM-DD; sample data
tasks(id, task, status, due_date)                  -- status is Pending, In Progress or Done; sample data"""

# VERIFY every fact below before publishing.
PORTFOLIO_SEED = [
    ("Experience", "Cloud Support Engineer, supporting Google Cloud Platform",
     "Over 2 years of customer-facing troubleshooting across data analytics and AI/ML products.",
     None),
    ("Skills", "Core specialties: Data Analytics and AI ML products",
     "Most experienced with BigQuery, Dataflow, Dataproc, DataFusion, Cloud Composer (Managed Airflow), "
     "Pub/Sub and Looker.",
     None),
    ("Skills", "Broader AI/ML product experience",
     "Also experienced with Vertex AI (Agent Platform), Dialogflow and CX Agent Studio, "
     "Speech-to-Text, Text-to-Speech, Document AI, and with Gemini Enterprise & NotebookLM.",
     None),
    ("Certification", "Google Cloud Associate Cloud Engineer", "Google Cloud certification.", None),
    ("Certification", "Google Cloud Generative AI Leader", "Google Cloud certification.", None),
    ("Education", "Carleton University", "2017-2021.", None),
    ("Project", "Portfolio Site V1 (Wix)", "Early web portfolio built with Wix.",
     "https://bowenlu6688.wixsite.com/my-site"),
    ("Project", "Portfolio Site V2 (GitHub Pages)", "Static portfolio hosted on GitHub Pages.",
     "https://bl986.github.io/portfolio2/"),
    ("Project", "LifeOps OS AI Portfolio Copilot",
     "This app: FastAPI, Gemini API, a custom MCP server, SQLite with guarded Text-to-SQL, "
     "markdown agent skills, pytest, deployed on Render.",
     "https://github.com/bl986/lifeops-copilot"),
]

EXPENSES_SEED = [
    ("2026-11-01", "Groceries", 85.50, "Weekly grocery run"),
    ("2026-11-03", "Transport", 24.00, "Monthly bus pass top-up"),
    ("2026-11-05", "Dining", 42.00, "Dinner out"),
    ("2026-11-06", "Groceries", 63.20, "Midweek groceries"),
    ("2026-11-07", "Software", 12.00, "Developer tools subscription"),
]

TASKS_SEED = [
    ("Review pytest coverage", "In Progress", "2026-11-15"),
    ("Add rate limiting to /chat", "Pending", "2026-11-20"),
    ("Write architecture diagram for README", "Pending", "2026-11-22"),
    ("Deploy first version to Render", "Done", "2026-11-07"),
]

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|replace|vacuum|reindex)\b",
    re.IGNORECASE,
)


class UnsafeSQLError(ValueError):
    """Raised when a query fails the SELECT-only safety check."""


def db_path() -> Path:
    """DB location. Override with LIFEOPS_DB_PATH (tests use a temp file)."""
    return Path(os.environ.get("LIFEOPS_DB_PATH", DEFAULT_DB_PATH))


def _seed_if_empty(conn, table, insert_sql, rows):
    if conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0:
        conn.executemany(insert_sql, rows)


def init_db() -> None:
    """Create tables and seed them once. Safe to call repeatedly."""
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as conn:
        conn.executescript(SCHEMA)
        _seed_if_empty(conn, "portfolio",
                       "INSERT INTO portfolio (category, title, description, link) VALUES (?, ?, ?, ?)",
                       PORTFOLIO_SEED)
        _seed_if_empty(conn, "expenses",
                       "INSERT INTO expenses (date, category, amount, description) VALUES (?, ?, ?, ?)",
                       EXPENSES_SEED)
        _seed_if_empty(conn, "tasks",
                       "INSERT INTO tasks (task, status, due_date) VALUES (?, ?, ?)",
                       TASKS_SEED)
        conn.commit()


def validate_select(sql: str) -> str:
    """Return a cleaned single SELECT statement, or raise UnsafeSQLError."""
    cleaned = (sql or "").strip().rstrip(";").strip()
    if not cleaned:
        raise UnsafeSQLError("Empty query.")
    if ";" in cleaned:
        raise UnsafeSQLError("Only a single statement is allowed.")
    if "--" in cleaned or "/*" in cleaned:
        raise UnsafeSQLError("SQL comments are not allowed.")
    if not re.match(r"select\b", cleaned, re.IGNORECASE):
        raise UnsafeSQLError("Only SELECT queries are allowed.")
    if _FORBIDDEN.search(cleaned):
        raise UnsafeSQLError("Query contains a forbidden keyword.")
    return cleaned


def connect_readonly() -> sqlite3.Connection:
    """Open the database in read-only mode (second layer of defence)."""
    uri = db_path().resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


def run_select(sql: str, limit: int = MAX_ROWS):
    """Validate and run a SELECT. Returns (sql, column_names, rows)."""
    safe_sql = validate_select(sql)
    with closing(connect_readonly()) as conn:
        cursor = conn.execute(safe_sql)
        columns = [c[0] for c in cursor.description] if cursor.description else []
        rows = cursor.fetchmany(limit)
    return safe_sql, columns, rows


if __name__ == "__main__":
    init_db()
    print(f"Database ready at {db_path()}")