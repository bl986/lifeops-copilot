import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from google import genai
from backend.mcp_server import get_portfolio, query_database

app = FastAPI(title="LifeOps OS Portfolio Agent", version="1.0")

class ChatRequest(BaseModel):
    message: str

@app.get("/", response_class=HTMLResponse)
def read_root():
    # Resolve index.html relative to this main.py file location
    html_path = Path(__file__).parent / "index.html"
    if html_path.exists():
        return html_path.read_text(encoding="utf-8")
    return "<h1>LifeOps OS API running (index.html not found)</h1>"

@app.post("/chat")
def chat_with_agent(request: ChatRequest):
    try:
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        user_msg = request.message.lower()
        
        context = ""
        if "portfolio" in user_msg or "project" in user_msg or "experience" in user_msg or "wix" in user_msg or "github" in user_msg:
            context = get_portfolio()
        elif "expense" in user_msg or "task" in user_msg or "spend" in user_msg or "show" in user_msg:
            context = query_database(request.message)
        else:
            context = get_portfolio()

        prompt = f"""
        You are the AI portfolio copilot for a Cloud Solution Engineer / Technical Support expert.
        Here is the retrieved data from the user's system based on their query:
        {context}
        
        User Query: "{request.message}"
        
        Provide a concise, professional, and engaging response to the hiring manager or visitor. Highlight technical competence and career background naturally.
        """
        
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt
        )
        
        return {
            "query": request.message,
            "response": response.text,
            "tool_context_used": context[:150] + "..."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
