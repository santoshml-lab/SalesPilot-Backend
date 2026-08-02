from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(title="SalesPilot AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL = "openai/gpt-oss-20b"


class ChatRequest(BaseModel):
    prompt: str


@app.get("/")
def root():
    return {
        "message": "SalesPilot AI API Running 🚀"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.post("/chat")
def chat(request: ChatRequest):
    try:

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
    "role": "system",
    "content": """
You are FlowPilot AI, an intelligent AI Business ERP Assistant.

You help users manage:
- Customers
- Products
- Inventory
- Sales
- Invoices
- Reports

Always introduce yourself as FlowPilot AI.
Never mention SalesPilot.
Be professional, helpful and concise.
"""
                }
                {
                                       
                
                    "role": "user",
                    "content": request.prompt
                }
            ],
            temperature=0.7,
            max_tokens=1000,
        )

        return {
            "response": response.choices[0].message.content
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
