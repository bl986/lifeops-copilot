# How this app was built

## Process
The first version was written with Gemini through chat prompts (vibe coding). A second AI assistant then reviewed the code and helped rebuild it. I decided what to apply and checked every change with diffs, tests, CI and live requests.

## Key bugs and fixes
- Generated SQL missed data: the model wrote a lowercase category value but the data was capitalized, and SQLite compares text case-sensitively, so a grocery total came back as zero. I found it by reading the generated SQL in the API response, then added case-insensitive matching to the schema, a prompt rule and a regression test.
- Silent file overwrites: early on, whole files pasted into a terminal replaced working code without warning. I moved to a browser editor with diffs and added tests and CI so regressions fail loudly.
- Stale frontend: a leftover index.html used the wrong element IDs, so the Send button did nothing.
- Wrong Python version: the host ignored runtime.txt and ran Python 3.14. A .python-version file fixed it, and the health endpoint proves it.
- Mocked tests hid a live failure: Google Search grounding returned quota errors while stubbed tests stayed green.
- A hidden tool failure: when a search failed, the model answered from memory as if it had searched. A prompt rule now requires saying so plainly.

## Lessons
Whole-file rewrites are risky. AI output needs checking. Read the generated SQL. Design for the failing tool. Keep secrets out of chats.