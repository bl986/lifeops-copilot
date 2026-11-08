import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend import agent

app = FastAPI(title="LifeOps OS Portfolio Agent", version="2.0")

base_dir = Path(__file__).parent
static_dir = base_dir / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)


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
def chat(request: ChatRequest):
    result = agent.run_agent(request.message)
    status_code = 200 if result["status"] == "success" else 503
    return JSONResponse(status_code=status_code, content=result)