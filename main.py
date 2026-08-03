from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv
from supabase import create_client
from fastapi.responses import FileResponse
from reportlab.pdfgen import canvas
import tempfile
import resend
import os

load_dotenv()
resend.api_key = os.getenv("RESEND_API_KEY")

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

def extract_product(prompt):
    response = supabase.table("products").select("*").execute()

    products = response.data or []

    prompt = prompt.lower()

    for product in products:
        if product["name"].lower() in prompt:
            return product["name"]

    return "No Product Found"

def extract_customer(prompt):
    response = supabase.table("customers").select("*").execute()

    customers = response.data or []

    prompt = prompt.lower().strip()

    for customer in customers:
        name = customer["name"].lower().strip()

        if name in prompt:
            return customer["name"]

    return "No Customer Found"

def create_sale(customer_name, product_name, qty):

    # Customer Find
    customer_data = (
        supabase.table("customers")
        .select("*")
        .eq("name", customer_name)
        .execute()
    )

    if not customer_data.data:
        return "❌ Customer Not Found"

    customer = customer_data.data[0]

    # Product Find
    product_data = (
        supabase.table("products")
        .select("*")
        .eq("name", product_name)
        .execute()
    )

    if not product_data.data:
        return "❌ Product Not Found"

    product = product_data.data[0]

    stock = int(product["stock"])

    if stock < qty:
        return "❌ Not enough stock available"

    total = qty * float(product["price"])
    invoice_no = f"INV-{customer['id']}{product['id']}{qty}"

    # Insert Sale
    supabase.table("sales").insert({
        "customer_id": customer["id"],
        "product_id": product["id"],
        "quantity": qty,
        "total": total
    }).execute()

    # Update Stock
    supabase.table("products").update({
        "stock": stock - qty
    }).eq("id", product["id"]).execute()
    supabase.table("invoices").insert({
    "invoice_no": invoice_no,
    "customer_name": customer_name,
    "product_name": product_name,
    "quantity": qty,
    "total": total,
    "status": "Paid"
  }).execute()

    return f"""
✅ Sale Created Successfully

🧾 Invoice No : {invoice_no}

👤 Customer : {customer_name}

📦 Product : {product_name}

🔢 Quantity : {qty}

💰 Total : ₹{total}

📄 Invoice Saved Successfully
"""


def get_customer_id(customer_name):
    response = (
        supabase.table("customers")
        .select("*")
        .eq("name", customer_name)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]["id"]

def get_product_name(product_id):
    response = (
        supabase.table("products")
        .select("*")
        .eq("id", product_id)
        .execute()
    )

    if not response.data:
        return "Unknown Product"

    return response.data[0]["name"]

def get_purchase_history(customer_name):

    customer_id = get_customer_id(customer_name)

    if customer_id is None:
        return "❌ Customer Not Found"

    response = (
        supabase.table("sales")
        .select("*")
        .eq("customer_id", customer_id)
        .execute()
    )

    sales = response.data or []

    if not sales:
        return "📭 No Purchase History Found"

    text = f"📜 Purchase History\n\n👤 Customer : {customer_name}\n\n"

    total_spent = 0

    for sale in sales:

        product_name = get_product_name(sale["product_id"])

        text += (
            f"📦 {product_name}\n"
            f"Quantity : {sale['quantity']}\n"
            f"Total : ₹{sale['total']}\n\n"
        )

        total_spent += float(sale["total"])

    text += f"💰 Total Spent : ₹{total_spent}"

    return text

def get_top_selling_products():

    response = supabase.table("sales").select("*").execute()

    sales = response.data or []

    if not sales:
        return "📭 No Sales Found"

    product_sales = {}

    for sale in sales:

        product_name = get_product_name(sale["product_id"])

        qty = int(sale["quantity"])

        if product_name in product_sales:
            product_sales[product_name] += qty
        else:
            product_sales[product_name] = qty

    sorted_products = sorted(
        product_sales.items(),
        key=lambda x: x[1],
        reverse=True
    )

    text = "🏆 Top Selling Products\n\n"

    rank = 1

    for product, qty in sorted_products[:5]:
        text += f"{rank}. {product}\nSold : {qty}\n\n"
        rank += 1

    return text

def get_monthly_sales():

    response = supabase.table("sales").select("*").execute()

    sales = response.data or []

    if not sales:
        return "📭 No Sales Found"

    monthly_sales = {}

    for sale in sales:

        created_at = sale["created_at"][:7]   # YYYY-MM

        total = float(sale["total"])

        if created_at in monthly_sales:
            monthly_sales[created_at] += total
        else:
            monthly_sales[created_at] = total

    text = "📊 Monthly Sales Report\n\n"

    for month, revenue in sorted(monthly_sales.items()):
        text += f"📅 {month} : ₹{revenue}\n"

    return text

def get_best_customer():

    response = supabase.table("sales").select("*").execute()

    sales = response.data or []

    if not sales:
        return "📭 No Sales Found"

    customer_spending = {}

    for sale in sales:

        customer_id = sale["customer_id"]
        total = float(sale["total"])

        if customer_id in customer_spending:
            customer_spending[customer_id] += total
        else:
            customer_spending[customer_id] = total

    best_customer_id = max(
        customer_spending,
        key=customer_spending.get
    )

    customer_response = (
        supabase.table("customers")
        .select("*")
        .eq("id", best_customer_id)
        .execute()
    )

    customer_name = customer_response.data[0]["name"]

    total_spent = customer_spending[best_customer_id]

    return f"""
🏆 Best Customer

👤 Name : {customer_name}

💰 Total Spending : ₹{total_spent}
"""

def get_business_summary():

    revenue = get_today_revenue()

    total_customers = get_total_customers()

    total_products, total_stock, low_stock = get_inventory_summary()

    top_products = get_top_selling_products()

    best_customer = get_best_customer()

    return f"""
📊 FlowPilot AI Business Summary

💰 Revenue : ₹{revenue}

👥 Customers : {total_customers}

📦 Products : {total_products}

📊 Stock Units : {total_stock}

🔴 Low Stock Items : {low_stock}

----------------------------------

{best_customer}

----------------------------------

{top_products}
"""

def get_ai_insights():

    revenue = get_today_revenue()

    customers = get_total_customers()

    products, stock, low_stock = get_inventory_summary()

    prompt = f"""
You are an ERP Business Analyst.

Business Data:

Revenue : ₹{revenue}

Customers : {customers}

Products : {products}

Stock Units : {stock}

Low Stock : {low_stock}

Give:

1. Business Summary
2. Risks
3. Opportunities
4. Recommendations

Keep response short.
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content

def get_recent_sales():

    response = (
        supabase.table("sales")
        .select("*")
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )

    sales = response.data or []

    result = []

    for sale in sales:

        customer = (
            supabase.table("customers")
            .select("name")
            .eq("id", sale["customer_id"])
            .execute()
        )

        product = (
            supabase.table("products")
            .select("name")
            .eq("id", sale["product_id"])
            .execute()
        )

        result.append({
            "customer": customer.data[0]["name"] if customer.data else "Unknown",
            "product": product.data[0]["name"] if product.data else "Unknown",
            "total": sale["total"]
        })

    return result

def get_best_customer():

    response = supabase.table("sales").select("*").execute()

    sales = response.data or []

    customer_total = {}

    for sale in sales:

        cid = sale["customer_id"]

        customer_total[cid] = customer_total.get(cid, 0) + float(sale["total"])

    if not customer_total:
        return None

    best_customer_id = max(customer_total, key=customer_total.get)

    customer = (
        supabase.table("customers")
        .select("*")
        .eq("id", best_customer_id)
        .execute()
    )

    return {
        "name": customer.data[0]["name"],
        "total": customer_total[best_customer_id]
    }

def get_top_product():

    response = supabase.table("sales").select("*").execute()

    sales = response.data or []

    product_sales = {}

    for sale in sales:

        pid = sale["product_id"]

        if pid not in product_sales:
            product_sales[pid] = {
                "quantity": 0,
                "revenue": 0
            }

        product_sales[pid]["quantity"] += int(sale["quantity"])
        product_sales[pid]["revenue"] += float(sale["total"])

    if not product_sales:
        return None

    top_id = max(
        product_sales,
        key=lambda x: product_sales[x]["quantity"]
    )

    product = (
        supabase.table("products")
        .select("*")
        .eq("id", top_id)
        .execute()
    )

    return {
        "name": product.data[0]["name"],
        "sold": product_sales[top_id]["quantity"],
        "revenue": product_sales[top_id]["revenue"]
    }

@app.get("/invoice/{invoice_no}")
def download_invoice(invoice_no: str):

    response = (
        supabase.table("invoices")
        .select("*")
        .eq("invoice_no", invoice_no)
        .execute()
    )

    if not response.data:
        raise HTTPException(status_code=404, detail="Invoice Not Found")

    invoice = response.data[0]

    pdf_path = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".pdf"
    ).name

    c = canvas.Canvas(pdf_path)

    c.setFont("Helvetica-Bold",18)
    c.drawString(200,800,"FlowPilot Invoice")

    c.setFont("Helvetica",12)

    c.drawString(50,750,f"Invoice : {invoice['invoice_no']}")
    c.drawString(50,725,f"Customer : {invoice['customer_name']}")
    c.drawString(50,700,f"Product : {invoice['product_name']}")
    c.drawString(50,675,f"Quantity : {invoice['quantity']}")
    c.drawString(50,650,f"Total : ₹{invoice['total']}")
    c.drawString(50,625,f"Status : {invoice['status']}")

    c.save()

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"{invoice_no}.pdf"
    )



@app.get("/top-product")
def top_product():
    return get_top_product()

@app.get("/best-customer")
def best_customer():
    return get_best_customer()

@app.get("/low-stock")
def low_stock():

    products = get_low_stock_products()

    result = []

    for item in products:

        result.append({
            "name": item["name"],
            "stock": item["stock"]
        })

    return result



@app.get("/recent-sales")
def recent_sales():
    return get_recent_sales()

@app.get("/insights")
def insights():

    return {
        "insights": get_ai_insights()
    }

@app.get("/dashboard")
def dashboard():

    revenue = get_today_revenue()

    customers = get_total_customers()

    products, stock, low_stock = get_inventory_summary()

    best_customer = get_best_customer()

    return {
        "revenue": revenue,
        "customers": customers,
        "products": products,
        "stock": stock,
        "low_stock": low_stock,
        "best_customer": best_customer
    }

@app.post("/send-invoice/{invoice_no}")
def send_invoice(invoice_no: str):

    invoice = (
        supabase.table("invoices")
        .select("*")
        .eq("invoice_no", invoice_no)
        .execute()
    )

    if not invoice.data:
        raise HTTPException(status_code=404, detail="Invoice Not Found")

    invoice = invoice.data[0]

    customer = (
        supabase.table("customers")
        .select("*")
        .eq("name", invoice["customer_name"])
        .execute()
    )

    if not customer.data:
        raise HTTPException(status_code=404, detail="Customer Not Found")

    email = "santoshkrsbg36@gmail.com"

    resend.Emails.send({
        "from": "FlowPilot <onboarding@resend.dev>",
        "to": [email],
        "subject": f"Invoice {invoice_no}",
        "html": f"""
        <h2>FlowPilot Invoice</h2>
        <p><b>Invoice:</b> {invoice['invoice_no']}</p>
        <p><b>Customer:</b> {invoice['customer_name']}</p>
        <p><b>Product:</b> {invoice['product_name']}</p>
        <p><b>Quantity:</b> {invoice['quantity']}</p>
        <p><b>Total:</b> ₹{invoice['total']}</p>
        <p>Thank you for choosing FlowPilot.</p>
        """
    })

    return {"message": "Invoice sent successfully"}
    
    
        
        
        






    
    
    

    
    

    
    



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

        # Purchase History Tool
        if "purchase history" in prompt:
            print("Purchase History Tool Called")

            customer = extract_customer(prompt)
            result = get_purchase_history(customer)

            return {
                "response": result
            }

                # Top Selling Products Tool
        if (
            "top selling" in prompt
            or "best selling" in prompt
            or "most sold" in prompt
        ):

            result = get_top_selling_products()

            return {
                "response": result
            }

                # Monthly Sales Analytics Tool
        if (
            "monthly sales" in prompt
            or "sales report" in prompt
            or "monthly report" in prompt
        ):

            result = get_monthly_sales()

            return {
                "response": result
            }

                # Best Customer Tool
        if (
            "best customer" in prompt
            or "top customer" in prompt
            or "highest spending customer" in prompt
        ):

            result = get_best_customer()

            return {
                "response": result
            }

                # Business Summary Tool
        if (
            "business summary" in prompt
            or "business report" in prompt
            or "how is my business" in prompt
            or "today summary" in prompt
        ):

            result = get_business_summary()

            return {
                "response": result
            }


        
        
    

    
    

          
        
    

            

            

            
                
            

        
       

    

    
    
            


    

                # Sell Product Command
        if "sell" in prompt:

            qty = extract_quantity(prompt)
            product = extract_product(prompt)
            customer = extract_customer(prompt)

            result = create_sale(customer, product, qty)

            return {
                "response": result
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

    

        

        
