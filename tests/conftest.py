import pytest

from backend import database


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Every test gets its own throwaway database."""
    monkeypatch.setenv("LIFEOPS_DB_PATH", str(tmp_path / "test.db"))
    database.init_db()