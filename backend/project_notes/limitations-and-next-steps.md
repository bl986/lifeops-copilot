# Limitations and next steps

## Known limitations
- Documentation retrieval is keyword-based over four pages. It can miss synonyms and its content can be up to 6 hours old.
- Rate limits are kept in memory, so they reset when the server restarts, and per-IP headers can be spoofed. The overall hourly cap is the real protection for my free quota.
- The free host sleeps after inactivity, so the first request can take up to about a minute.
- The database is rebuilt from seed data on every deploy. It holds demo data and is not persistent storage.
- The GitHub connector needs a token. Without one, GitHub allows only 60 requests an hour per IP address, which shared hosting can use up.
- Google Search grounding is implemented but switched off, because my free API key did not have the quota for it.
- Skills are loaded into every prompt instead of on demand.
- The web app is not itself an MCP client.
- I did not use Google's Agent Development Kit. The agent uses the google-genai SDK directly.

## What I would improve next
- A larger evaluation set with expected tools and answers, and a printed pass rate.
- A load test, and a measured note on what the free instance can handle.
- Loading skills on demand.
- Making the web app a true MCP client.
- A persistent database if the app ever stores user data.