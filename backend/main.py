import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="LifeOps OS Portfolio Agent", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

base_dir = Path(__file__).parent
static_dir = base_dir / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

class ChatRequest(BaseModel):
    message: str

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

@app.get("/", response_class=HTMLResponse)
def read_root():
    paths_to_check = [
        base_dir / "index.html",
        base_dir.parent / "index.html",
        Path("backend/index.html"),
        Path("index.html")
    ]
    for p in paths_to_check:
        if p.exists():
            return p.read_text(encoding="utf-8")
    return "<h1>LifeOps OS API running (index.html not found)</h1>"

@app.post("/chat")
def chat_with_agent(request: ChatRequest):
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return JSONResponse(
                status_code=500,
                content={"response": "Error: GEMINI_API_KEY environment variable not set on Render."}
            )
            
        from google import genai
        from google.genai import types
        from backend.mcp_server import get_portfolio, query_database
        from backend.skills_loader import load_agent_skills
        from backend.harness import AgentHarness
        
        # Initialize Harness & Load Skills
        harness = AgentHarness(agent_name="LifeOps-Portfolio-Copilot")
        skills_prompt = load_agent_skills()
        
        user_msg = request.message.lower()
        
        # Retrieve MCP context
        if "portfolio" in user_msg or "project" in user_msg or "experience" in user_msg or "wix" in user_msg or "github" in user_msg:
            context = get_portfolio()
        elif "expense" in user_msg or "task" in user_msg or "spend" in user_msg or "show" in user_msg:
            context = query_database(request.message)
        else:
            context = get_portfolio()

        # Define generation logic to be wrapped by the harness
        def run_generation():
            client = genai.Client(api_key=api_key)
            prompt = f"""
            You are the AI portfolio copilot for Bowen Lu.
            
            --- RETRIEVED DATA ---
            {context}
            
            --- AGENT SKILLS & GUIDELINES ---
            {skills_prompt}
            
            User Query: "{request.message}"
            
            Provide a concise, professional, and engaging response.
            
            CRITICAL FORMATTING RULES:
            1. Use markdown bolding (**text**) for job titles, certifications, and key skills. NEVER turn job titles or certifications into hyperlinks.
            2. ONLY use markdown links for actual external portfolio URLs, such as GitHub or Wix portfolios (e.g., [GitHub Portfolio](https://bl986.github.io/portfolio2/) or [Wix Portfolio](https://bowenlu6688.wixsite.com/my-site)).
            3. Generalize location references to just Canada.
            """
            
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=1500,
                    temperature=0.7
                )
            )
            return response.text

        # Execute through the harness wrapper
        harness_result = harness.execute(request.message, run_generation)
        
        return {
            "query": request.message,
            "response": harness_result["response"],
            "latency": harness_result["latency_seconds"],
            "tool_context_used": context[:150] + "..."
        }
    except Exception as e:
        print(f"CRITICAL ERROR in /chat: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"response": f"Server Error: {str(e)}"}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
