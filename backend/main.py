import os
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend import agent
from backend.ratelimit import RateLimiter

app = FastAPI(title="LifeOps OS Portfolio Agent", version="2.1")

base_dir = Path(__file__).parent
static_dir = base_dir / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Tunable from Render's Environment tab without code changes.
ip_limiter = RateLimiter(int(os.environ.get("RATE_LIMIT_PER_MINUTE", "10")), 60)
global_limiter = RateLimiter(int(os.environ.get("RATE_LIMIT_GLOBAL_PER_HOUR", "300")), 3600)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)


def client_key(http_request: Request) -> str:
    """Best-effort client id. Behind Render's proxy the real IP is in X-Forwarded-For."""
    forwarded = http_request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return http_request.client.host if http_request.client else "unknown"


def too_many(retry_after: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        headers={"Retry-After": str(retry_after)},
        content={"status": "rate_limited", "response": message, "tools_called": []},
    )


@app.get("/", include_in_schema=False)
def read_root():
    return FileResponse(base_dir / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.get("/health")
def health():
    return {"status": "ok", "python": sys.version.split()[0], "model": agent.MODEL}


@app.post("/chat")
def chat(request: ChatRequest, http_request: Request):
    wait = ip_limiter.check(client_key(http_request))
    if wait:
        return too_many(wait, f"You're sending messages too quickly. Please wait about {wait} seconds.")
    wait = global_limiter.check("global")
    if wait:
        return too_many(wait, "The demo has hit its hourly usage cap. Please try again later.")

    result = agent.run_agent(request.message)
    status_code = 200 if result["status"] == "success" else 503
    return JSONResponse(status_code=status_code, content=result)