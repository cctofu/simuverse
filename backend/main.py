from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from query import query
from ask import PersonaChat, ask_persona

app = FastAPI(title="Persona Analysis API")
app.add_middleware(
      CORSMiddleware,
      allow_origins=["http://localhost:5173", "http://localhost:5174"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
)

# Store active conversation sessions
# In production, use Redis or a database instead
active_sessions = {}

class ProductRequest(BaseModel):
    product_description: str

class AskPersonaRequest(BaseModel):
    pid: str
    question: str
    session_id: Optional[str] = None  # If provided, maintains conversation context

class ConversationMessage(BaseModel):
    role: str
    content: str

@app.post("/analyze_product")
async def analyze_product(request: ProductRequest):
    try:
        product_description = request.product_description
        if not product_description:
            raise HTTPException(status_code=400, detail="Missing 'product_description' in request body")
        result = query(product_description)
        return result
    except Exception as e:
        print(f"❌ Handler error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/ask_persona")
async def ask_persona_endpoint(request: AskPersonaRequest):
    """
    Ask a persona a question in a multi-turn conversation.

    - If session_id is provided, continues existing conversation
    - If session_id is not provided, creates a new conversation and returns a new session_id
    """
    try:
        pid = request.pid
        question = request.question
        session_id = request.session_id

        if not pid or not question:
            raise HTTPException(status_code=400, detail="Both 'pid' and 'question' are required")

        # If no session_id provided, create a new session
        if not session_id:
            import uuid
            session_id = str(uuid.uuid4())

        # Get or create session
        if session_id not in active_sessions:
            try:
                active_sessions[session_id] = PersonaChat(pid)
            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e))

        chat = active_sessions[session_id]

        # Verify the session is for the same persona
        if chat.pid != pid:
            raise HTTPException(
                status_code=400,
                detail=f"Session {session_id} is for persona {chat.pid}, not {pid}"
            )

        # Get response
        response = chat.ask(question)
        history = chat.get_history()

        return {
            "pid": pid,
            "session_id": session_id,
            "response": response,
            "history": history
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Handler error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a conversation session to free up memory.
    """
    if session_id in active_sessions:
        del active_sessions[session_id]
        return {"message": f"Session {session_id} deleted"}
    else:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

@app.get("/")
async def root():
    return {"status": "ok", "message": "Persona Analysis API is running"}
