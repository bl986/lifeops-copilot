# Architecture

## Overview
LifeOps OS is a FastAPI web app. A visitor types a message in the browser chat. The server checks the message and applies rate limits, then hands it to an agent built on Gemini function calling. The model decides which tool to call: portfolio data, a SQL query on sample data, live GitHub data, passages from Google Cloud documentation, or notes about this project. It reads the tool result and writes the answer. The reply comes back with sources and suggested follow-up questions.

## Request flow
1. The browser sends the message and the list of switched-on connectors to the chat endpoint.
2. main.py checks the length (at most 500 characters) and applies rate limits: 10 requests a minute per IP address and 300 an hour overall.
3. agent.py builds the tool list from the enabled connectors only, so a switched-off connector cannot be used.
4. Gemini is called with the system prompt, the skill files and a note about which connectors are off. It can call up to 3 tools.
5. The harness times the run and turns errors or an empty reply into a safe message.
6. The server returns the answer, the tools that were called, the sources and three follow-up prompts.

## Main components
- main.py: the web server, input validation, rate limits, the connectors list and a health check that reports the Python version.
- agent.py: Gemini function calling. It builds the tools from the enabled connectors and returns sources and follow-up prompts.
- connectors.py: the registry of switchable connectors with their names and defaults.
- mcp_server.py: a FastMCP server exposing the portfolio and SQL tools, so any MCP client can use them.
- database.py: the SQLite schema, seed data, the SELECT-only validator and the read-only connection.
- github_tools.py: live data from my public GitHub repositories, cached.
- docs_tools.py: retrieval over four official Google Cloud documentation pages.
- project_tools.py: retrieval over these project notes.
- grounding.py: an optional Google Search grounding tool, switched off by default.
- harness.py: wraps each run to measure time and catch errors.
- ratelimit.py: an in-memory sliding-window rate limiter.
- skills_loader.py: loads markdown skill files into the system prompt.
- workflows.py: fixed multi-step workflows (profile brief, project deep dive) that gather data in code and stream progress to the page.

## Data and storage
The data lives in a SQLite file that is rebuilt from seed data when the server starts. It holds portfolio rows plus demo expenses and tasks. Nothing a visitor types is stored. GitHub and documentation data are fetched live and cached in memory.

## Diagram
The README on GitHub has an architecture diagram: https://github.com/bl986/lifeops-copilot#architecture