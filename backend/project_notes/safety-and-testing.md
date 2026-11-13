# Safety and testing

## How the SQL tool stays safe
The model writes the SQL. A validator then allows only a single SELECT statement, with no comments and no write or schema keywords. The query runs on a SQLite connection opened in read-only mode, and results are capped at 50 rows. Tests feed it injection attempts such as DROP, DELETE, UPDATE, stacked statements, comments and PRAGMA.

## Other protections
- Messages are limited to 500 characters.
- Rate limits are 10 requests a minute per IP address and 300 an hour overall, and the Google Search grounding tool has its own hourly cap.
- The documentation connector only fetches a fixed list of Google URLs and rejects redirects outside Google domains. The GitHub tool only accepts names of my own public repositories.
- Model output is HTML-escaped before it is shown, and links must be http or https.
- Errors are logged on the server and visitors see a generic message.
- Secrets such as the API key live only in the host's masked environment settings.

## Prompt injection
The system prompt tells the model to treat user messages and tool results as data, not instructions. That is a mitigation, not a guarantee. The real protection is in code: tools are limited to enabled connectors, SQL is validated and read-only, and fetches are allowlisted.

## How it is tested
pytest tests cover the SQL validator, the read-only connection, each tool, the harness, rate limiting, connector toggling, GitHub caching and failure handling, documentation ranking and caching, and these project notes. GitHub Actions runs them on every push. External services are stubbed in CI so the tests are free and repeatable. A separate live evaluation checks that the real model picks the right tool, and it runs only when an API key is set.

## What tests cannot catch
Mocked tests passed while the live Google Search call was failing, because the real quota was missing. So I check each live integration separately and the app tells visitors when a tool is unavailable instead of answering from memory.