import os
import pytest
import sqlite3
import sys

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from database import DB_PATH, init_db
from mcp_server import get_portfolio, query_database

@pytest.fixture(autouse=True)
def setup_database():
    """Ensures a clean database is initialized before each test."""
    init_db()

def test_database_connection():
    """Verify SQLite database exists and contains seeded tables."""
    assert os.path.exists(DB_PATH), "Database file not found!"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    assert "portfolio" in tables
    assert "expenses" in tables
    assert "tasks" in tables

def test_get_portfolio_tool():
    """Verify portfolio tool returns professional history and Wix/GitHub links."""
    result = get_portfolio()
    assert "Portfolio Site V1" in result
    assert "Portfolio Site V2" in result
    assert "GCP Technical Support Representative" in result
    assert "https://bowenlu6688.wixsite.com/my-site" in result

def test_query_database_safety():
    """Test standard SQL retrieval via natural language input."""
    result = query_database("Show all tasks")
    assert "Prepare SAAQ Class 5 knowledge exam review" in result
