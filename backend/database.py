import sqlite3

def init_db():
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, name TEXT, tech TEXT)")
    cursor.execute("INSERT OR IGNORE INTO projects VALUES (1, 'LifeOps Copilot', 'FastAPI, Gemini API, Render')")
    conn.commit()
    conn.close()

def run_sql(query: str):
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        return cursor.fetchall()
    except Exception as e:
        return str(e)
    finally:
        conn.close()
