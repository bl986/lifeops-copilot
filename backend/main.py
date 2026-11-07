import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import genai
from mcp_server import get_portfolio, query_database

app = FastAPI(title="LifeOps OS Portfolio Agent", version="1.0")

class ChatRequest(BaseModel):
    message: str

@app.get("/")
def read_root():
    return {"status": "online", "message": "Welcome to LifeOps OS API. Use /chat to interact with the agent."}

@app.post("/chat")
def chat_with_agent(request: ChatRequest):
    try:
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        user_msg = request.message.lower()
        
        # Simple intelligent router mapping user intents to your tools
        context = ""
        if "portfolio" in user_msg or "project" in user_msg or "experience" in user_msg or "wix" in user_msg or "github" in user_msg:
            context = get_portfolio()
        elif "expense" in user_msg or "task" in user_msg or "spend" in user_msg or "show" in user_msg:
            context = query_database(request.message)
        else:
            # Default fallback: provide portfolio context + general assistance
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
            "tool_context_used": context[:150] + "..." # snippet of tool inspection
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
