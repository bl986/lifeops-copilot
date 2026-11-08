"""Custom MCP server exposing portfolio and database tools.

Run standalone (stdio transport):  python -m backend.mcp_server
The FastAPI app also imports these functions directly.
"""
import os
import re
import sqlite3

from mcp.server.fastmcp import FastMCP

from backend.database import SCHEMA_DESCRIPTION, UnsafeSQLError, init_db, run_select

mcp = FastMCP("LifeOps MCP Server")

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")

SQL_PROMPT = """You translate a question into ONE SQLite SELECT statement.

{schema}

Rules:
- Return only the SQL. No explanation, no markdown.
- Use only the tables and columns above.
- Never write INSERT, UPDATE, DELETE, DROP or any statement that changes data.
- Compare text case-insensitively.

Question: {question}"""


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:sql)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def generate_sql(question: str) -> str:
    """Ask Gemini to write SQL for the question (patched out in tests)."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    from google import genai

    client = genai.Client(api_key=api_key)
    prompt = SQL_PROMPT.format(schema=SCHEMA_DESCRIPTION, question=question)
    response = client.models.generate_content(model=MODEL, contents=prompt)
    return _strip_code_fences(response.text)


@mcp.tool()
def get_portfolio() -> str:
    """Return Bowen Lu's professional background: experience, certifications, education, projects and links."""
    init_db()
    _, _, rows = run_select("SELECT category, title, description, link FROM portfolio ORDER BY id")
    lines = ["Bowen Lu, based in Canada."]
    for category, title, description, link in rows:
        line = f"- [{category}] {title}: {description}"
        if link:
            line += f" ({link})"
        lines.append(line)
    return "\n".join(lines)


@mcp.tool()
def query_database(natural_language_query: str) -> str:
    """Answer a question about the portfolio, expenses or tasks tables by generating and running a safe, read-only SQL query."""
    init_db()
    try:
        sql = generate_sql(natural_language_query[:500])
        safe_sql, columns, rows = run_select(sql)
    except UnsafeSQLError as e:
        return f"Query rejected by safety check: {e}"
    except sqlite3.Error as e:
        return f"The generated query could not be run: {e}"
    except Exception as e:  # API errors, missing key, etc.
        print(f"query_database error: {e}")
        return "Could not generate a query right now."
    return f"SQL: {safe_sql}\nColumns: {columns}\nRows: {rows}"


if __name__ == "__main__":
    mcp.run()