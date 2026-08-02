from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv
from supabase import create_client
import os

load_dotenv()

app = FastAPI(title="FlowPilot AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

MODEL = "openai/gpt-oss-20b"


class ChatRequest(BaseModel):
    prompt: str


@app.get("/")
def root():
    return {
        "message": "FlowPilot AI API Running 🚀"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


def get_low_stock_products():
    response = supabase.table("products").select("*").execute()
        
          
        
    

    products = response.data or []

    low_stock = [
        p for p in products
        if int(p["stock"]) <= int(p["low_stock_limit"])
    ]

    return low_stock
def get_today_revenue():
    response = supabase.table("sales").select("*").execute()

    sales = response.data or []

    revenue = sum(float(item["total"]) for item in sales)

    return revenue


@app.post("/chat")
def chat(request: ChatRequest):
    try:

        prompt = request.prompt.lower()

        if "low stock" in prompt:
            low_stock = get_low_stock_products()
        if "today revenue" in prompt or "revenue" in prompt:
           revenue = get_today_revenue()

    return {
        "response": f"💰 Total Revenue: ₹{revenue}"
    }

            if not low_stock:
                return {
                    "response": "✅ No low stock products found."
                }

            text = "🔴 Low Stock Products:\n\n"

            for item in low_stock:
                text += (
                    f"• {item['name']} "
                    f"(Stock: {item['stock']})\n"
                )

            return {
                "response": text
            }

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
                },
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
