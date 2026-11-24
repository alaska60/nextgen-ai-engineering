import os
import httpx

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="NEXTGEN AI BRAIN")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = os.getenv("AI_MODEL", "openai/gpt-oss-20b")


class ChatRequest(BaseModel):
    message: str


@app.get("/")
def home():
    return {
        "name": "NEXTGEN AI BRAIN",
        "status": "online"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/api/chat")
async def chat(data: ChatRequest):

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="AI key is not configured"
        )

    if not data.message.strip():
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty"
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are NEXTGEN AI CREATOR, "
                    "a helpful AI assistant. "
                    "Understand Cebuano and English. "
                    "Help with coding, games, apps, "
                    "creative projects and analysis. "
                    "Be honest about errors and limitations."
                )
            },
            {
                "role": "user",
                "content": data.message
            }
        ],
        "temperature": 0.5,
        "max_completion_tokens": 2000
    }

    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                GROQ_URL,
                headers=headers,
                json=payload
            )

                if response.status_code != 200:
            try:
                error_data = response.json()
                error_message = error_data.get("error", {}).get(
                    "message", "Unknown Groq error"
                )
            except ValueError:
                error_message = "Unable to read Groq error"

            raise HTTPException(
                status_code=502,
                detail=f"Groq error {response.status_code}: {error_message[:300]}"
            )
            
                
        
            )

        result = response.json()

        return {
            "reply": result["choices"][0]["message"]["content"],
            "model": MODEL
        }

    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="Could not connect to AI provider"
)
