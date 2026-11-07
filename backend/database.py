import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "../data/lifeops.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Portfolio Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS portfolio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        title TEXT,
        description TEXT,
        link TEXT
    )
    """)

    # 2. Expenses Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        category TEXT,
        amount REAL,
        description TEXT
    )
    """)

    # 3. Tasks Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task TEXT,
        status TEXT,
        due_date TEXT
    )
    """)

    # Seed Sample Data
    cursor.execute("DELETE FROM portfolio")
    cursor.execute("DELETE FROM expenses")
    cursor.execute("DELETE FROM tasks")

    sample_portfolio = [
        ("Project", "Portfolio Site V1", "Early web portfolio built with Wix.", "https://bowenlu6688.wixsite.com/my-site"),
        ("Project", "Portfolio Site V2", "Static GitHub portfolio page.", "https://bl986.github.io/portfolio2/"),
        ("Experience", "GCP Technical Support Representative", "Troubleshooting Data Analytics, BigQuery, and Gemini Enterprise.", "https://cloud.google.com"),
        ("Certification", "Google Cloud Associate Cloud Engineer", "Certified cloud professional.", "https://cloud.google.com")
    ]
    cursor.executemany("INSERT INTO portfolio (category, title, description, link) VALUES (?, ?, ?, ?)", sample_portfolio)

    sample_expenses = [
        ("2026-11-01", "Groceries", 85.50, "Weekly supermarket run"),
        ("2026-11-03", "Transport", 24.00, "Bus monthly pass top-up"),
        ("2026-11-05", "Dining", 42.00, "Dinner with former colleague")
    ]
    cursor.executemany("INSERT INTO expenses (date, category, amount, description) VALUES (?, ?, ?, ?)", sample_expenses)

    sample_tasks = [
        ("Prepare SAAQ Class 5 knowledge exam review", "In Progress", "2026-11-15"),
        ("Refactor LifeOps MCP server error handling", "Pending", "2026-11-10")
    ]
    cursor.executemany("INSERT INTO tasks (task, status, due_date) VALUES (?, ?, ?)", sample_tasks)

    conn.commit()
    conn.close()
    print("Database initialized and seeded successfully!")

if __name__ == "__main__":
    init_db()
