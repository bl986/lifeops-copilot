import sqlite3
import os
from mcp.server.fastmcp import FastMCP
from google import genai

mcp = FastMCP("LifeOps MCP Server")
DB_PATH = os.path.join(os.path.dirname(__file__), "../data/lifeops.db")

@mcp.tool()
def query_database(natural_language_query: str) -> str:
    """Translates a natural language question into a SQLite SQL query and returns the results."""
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    schema_info = "Tables: portfolio(id, category, title, description, link), expenses(id, date, category, amount, description), tasks(id, task, status, due_date)"
    
    prompt = f"Given SQLite schema:\n{schema_info}\nWrite a valid SQLite SELECT query to answer: \"{natural_language_query}\". Return ONLY raw SQL without markdown blocks."
    
    response = client.models.generate_content(model="gemini-3.8-flash", contents=prompt)
    sql_query = response.text.replace("`sql", "").replace("`", "").strip()
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        conn.close()
        return f"SQL: {sql_query}\nResults: {rows}"
    except Exception as e:
        return f"Error executing SQL ({sql_query}): {str(e)}"

@mcp.tool()
def get_portfolio() -> str:
    """Retrieves professional history, projects, and certifications."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT category, title, description, link FROM portfolio")
    rows = cursor.fetchall()
    conn.close()
    
    result = "### Professional Portfolio & Experience\n"
    for row in rows:
        result += f"- **[{row[0]}] {row[1]}**: {row[2]} ([Link]({row[3]}))\n"
    return result

if __name__ == "__main__":
    mcp.run()
