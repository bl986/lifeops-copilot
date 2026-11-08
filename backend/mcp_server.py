from backend.database import init_db, run_sql

# Initialize the database on startup
init_db()

def get_portfolio() -> str:
    """Returns Bowen's professional portfolio and career background."""
    return """
    Bowen Lu is a Cloud Support Engineer and Technical Support expert based in Quebec, Canada.
    - Experience: 2+ years as a GCP Technical Support Representative, specializing in Data Analytics shards (BigQuery, Cloud Composer, Airflow, GKE, Dataflow, Pub/Sub) and transitioning into Gemini Enterprise & AI/ML troubleshooting.
    - Certifications: Google Cloud Associate Cloud Engineer, Gen AI Lead certification.
    - Education: Carleton University (2017-2024).
    - Portfolio Sites: 
      - GitHub Portfolio: https://bl986.github.io/portfolio2/
      - Wix Portfolio: https://bowenlu688.wixsite.com/my-site
    - Current Active Projects: LifeOps OS AI Portfolio Copilot, preparing for the Quebec SAAQ Class 5 driver's license test.
    """

def query_database(natural_query: str) -> str:
    """
    Simulates AI-driven SQL query generation and execution against the local SQLite database.
    """
    query_lower = natural_query.lower()
    
    # In a full agentic setup, Gemini can write the SQL directly. 
    # Here, we map natural language to structured SQL queries executed on our sqlite database:
    sql = ""
    if "project" in query_lower:
        sql = "SELECT * FROM projects;"
    else:
        sql = "SELECT name, tech FROM projects;"
        
    results = run_sql(sql)
    return f"Executed SQL: `{sql}`\nDatabase Results: {results}"
