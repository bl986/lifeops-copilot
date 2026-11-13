# Design decisions

## Why SQLite
SQLite needs no separate database server, it ships with Python, and the whole database is one file. The data here is small and mostly read-only demo data, so a server database would add cost and setup without adding anything. It also makes a read-only connection easy, which protects against bad model-written SQL. The trade-off: free hosting does not keep files between deploys, so the database is rebuilt from seed data each time, and SQLite is not built for many simultaneous writers. For real workloads I would move to Postgres or BigQuery.

## Why FastAPI
FastAPI validates input with Pydantic (for example the 500-character message limit), it is fast to write, and it generates a built-in test page at the docs URL that I used to test the live API. It is also a common choice for Python AI backends.

## Why function calling instead of keyword routing
The first version picked data with if statements on words in the message. With function calling the model chooses the tool and the arguments, handles greetings without any tool, and adding a new tool only means registering it. The trade-offs: a tool call costs an extra model round trip (about one to two seconds), and tool choice is less predictable than an if statement. So I cap tool calls at 3 and test which tool gets called.

## Why a SELECT-only validator plus a read-only connection
SQL written by a model is untrusted input. The validator allows one SELECT statement and rejects comments and write or schema keywords. The read-only connection is a second layer, so even if the validator were bypassed the database could not be changed. Two independent layers mean one mistake does not break safety.

## Why switchable connectors
Each data source is a connector the visitor can switch on or off, like data sources in an enterprise AI assistant. The server only gives the model the tools for enabled connectors, so a disabled connector cannot be used. If a question needs one that is off, the agent says which switch to turn on. It also lets me keep an expensive or unreliable connector off by default.

## Why keyword ranking instead of embeddings for documentation
The documentation connector uses a BM25-style keyword score over four pages. The set of pages is small and fixed, it costs no extra API quota, there is no index to rebuild, and tests are deterministic. The trade-off: keyword search misses synonyms, and the score does not measure relevance, so I use it only as a debugging aid and rely on prompt rules for partial matches.

## Why tools run in-process and also through MCP
The web app calls the tool functions directly because that is simple and fast. The same functions are exposed through a FastMCP server so any MCP client could use them. The trade-off: the web app is not itself an MCP client. Making it one is a possible next step.

## Why Render
Render's free tier deploys automatically from GitHub on every push, which gives a real live demo at no cost. The trade-offs: the free instance sleeps after inactivity, so the first request can take up to about a minute, and its IP address is shared, which is why the GitHub connector needs a token to avoid rate limits.

## Why Gemini
Gemini has a free tier and supports function calling. Model names and availability change often, so the model name is an environment variable instead of being hardcoded.

## Why suggested follow-ups come from a fixed list
The follow-up chips are picked from a tested list in code, so every suggestion is a question the agent is known to handle, and no extra model call is needed.

## Why fixed workflows next to the agent
Some tasks have the same steps every time, such as a recruiter brief. In a workflow, code runs the steps in a fixed order (read the profile, fetch GitHub activity, retrieve notes) and one model call with no tools writes the summary. Runs are predictable, quicker and cheaper than letting the model choose each step, and the page can show real progress. The trade-off: a workflow cannot adapt to an unexpected question, which is what the chat agent is for. Workflows are read-only and use the same rate limits and connector switches.