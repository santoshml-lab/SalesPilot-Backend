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


def get_total_customers():
    response = supabase.table("customers").select("*").execute()

    customers = response.data or []

    return len(customers)


def get_inventory_summary():
    response = supabase.table("products").select("*").execute()

    products = response.data or []

    total_products = len(products)

    total_stock = sum(
        int(product["stock"])
        for product in products
    )

    low_stock = sum(
        1
        for product in products
        if int(product["stock"])
        <= int(product["low_stock_limit"])
    )

    return total_products, total_stock, low_stock

def find_product(product_name):
    response = supabase.table("products").select("*").execute()

    products = response.data or []

    product_name = product_name.lower()

    for product in products:
        if product_name in product["name"].lower():
            return product

    return None

def find_customer(customer_name):
    response = supabase.table("customers").select("*").execute()

    customers = response.data or []

    customer_name = customer_name.lower()

    for customer in customers:
        if customer_name in customer["name"].lower():
            return customer

    return None

import re

def extract_quantity(prompt):
    match = re.search(r"\d+", prompt)

    if match:
        return int(match.group())

    return 1
    



@app.post("/chat")
def chat(request: ChatRequest):
    try:
        prompt = request.prompt.lower()

        # Low Stock Tool
        if "low stock" in prompt:
            low_stock = get_low_stock_products()

            if not low_stock:
                return {
                    "response": "✅ No low stock products found."
                }

            text = "🔴 Low Stock Products:\n\n"

            for item in low_stock:
                text += f"• {item['name']} (Stock: {item['stock']})\n"

            return {
                "response": text
            }

        # Revenue Tool
        if "today revenue" in prompt or "revenue" in prompt:
            revenue = get_today_revenue()

            return {
                "response": f"💰 Total Revenue: ₹{revenue}"
            }

        # Customers Tool
        if "customers" in prompt or "total customers" in prompt:
            total_customers = get_total_customers()

            return {
                "response": f"👥 Total Customers: {total_customers}"
            }

        # Inventory Summary Tool
        if (
            "inventory" in prompt
            or "inventory summary" in prompt
            or "stock" in prompt
        ):
            total_products, total_stock, low_stock = get_inventory_summary()

            return {
                "response": f"""📦 Inventory Summary

📦 Total Products : {total_products}

📊 Total Stock Units : {total_stock}

🔴 Low Stock Products : {low_stock}
"""
            }
                    # Sell Product Command
        # Sell Product Command
if "sell" in prompt:

    qty = extract_quantity(prompt)

    return {
        "response": f"🛒 Quantity Detected: {qty}"
    }
            
                
            

        

        


        

    
        
    




        
            

    
        
    
            
     
        
    

        

    
        
    

        # Normal AI Chat
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

    

        

        
