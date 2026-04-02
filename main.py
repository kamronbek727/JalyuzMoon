import os
import httpx
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request, Depends, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
# Supabase configuration from env
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# Supabase REST API setup
SUPABASE_REST_URL = f"{SUPABASE_URL}/rest/v1"
SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

app = FastAPI(title="Moon Jalyuzi Backend")

# CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class OrderItem(BaseModel):
    name: str
    qty: int
    price: float

class OrderSchema(BaseModel):
    client_name: str
    client_phone: str
    region: str
    address: str
    items: List[OrderItem]
    total: float
    status: Optional[str] = "new"

class LoginSchema(BaseModel):
    name: str
    password: str

# Helper: Send Telegram Message
async def send_telegram_msg(msg: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": ADMIN_CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            return response.json()
        except Exception as e:
            print(f"Telegram error: {e}")
            return None

# Auth dependency
async def verify_admin(request: Request):
    admin_auth = request.headers.get("X-Admin-Password")
    if admin_auth != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

# --- API ENDPOINTS ---

@app.post("/api/order")
async def create_order(order: OrderSchema):
    try:
        order_data = order.dict()
        order_data["items"] = [item.dict() for item in order.items]
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SUPABASE_REST_URL}/orders",
                headers=SUPABASE_HEADERS,
                json=order_data
            )
            
            if response.status_code not in [200, 201]:
                raise HTTPException(status_code=500, detail="Supabase restoration error: " + response.text)
            
            saved_order = response.json()[0]
            order_id = saved_order.get("id")

        items_list = "\n".join([f"▫️ {item.name} ({item.qty} x {item.price})" for item in order.items])
        msg = (
            f"📦 <b>Yangi Buyurtma: #{order_id}</b>\n\n"
            f"👤 <b>Mijoz:</b> {order.client_name}\n"
            f"📞 <b>Tel:</b> {order.client_phone}\n"
            f"📍 <b>Manzil:</b> {order.region}, {order.address}\n\n"
            f"🛒 <b>Mahsulotlar:</b>\n{items_list}\n\n"
            f"💰 <b>Jami: {int(order.total):,} so'm</b>"
        )
        await send_telegram_msg(msg)
        return {"status": "success", "order_id": order_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/login")
async def login(data: LoginSchema):
    if data.name.lower() == "admin" and data.password == ADMIN_PASSWORD:
        return {"status": "success", "role": "admin", "password": ADMIN_PASSWORD}
    return {"status": "success", "role": "user", "name": data.name, "phone": data.password}

@app.get("/api/products")
async def get_products():
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{SUPABASE_REST_URL}/products?select=*", headers=SUPABASE_HEADERS)
            if res.status_code != 200:
                print(f"Supabase Error: {res.text}")
                return []
            return res.json()
    except Exception as e:
        print(f"Products API Error: {e}")
        return []

@app.post("/api/products", dependencies=[Depends(verify_admin)])
async def save_product(data: Dict[Any, Any]):
    product_id = data.get("id")
    payload = {k: v for k, v in data.items() if k != "id"}
    async with httpx.AsyncClient() as client:
        if product_id:
            res = await client.patch(
                f"{SUPABASE_REST_URL}/products?id=eq.{product_id}",
                headers=SUPABASE_HEADERS,
                json=payload
            )
        else:
            res = await client.post(f"{SUPABASE_REST_URL}/products", headers=SUPABASE_HEADERS, json=payload)
        return res.json()

@app.delete("/api/products/{id}", dependencies=[Depends(verify_admin)])
async def delete_product(id: int):
    async with httpx.AsyncClient() as client:
        await client.delete(f"{SUPABASE_REST_URL}/products?id=eq.{id}", headers=SUPABASE_HEADERS)
    return {"status": "success"}

@app.get("/api/categories")
async def get_categories():
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{SUPABASE_REST_URL}/categories?select=*", headers=SUPABASE_HEADERS)
        return res.json()

@app.post("/api/categories", dependencies=[Depends(verify_admin)])
async def add_category(data: Dict[Any, Any]):
    async with httpx.AsyncClient() as client:
        res = await client.post(f"{SUPABASE_REST_URL}/categories", headers=SUPABASE_HEADERS, json=data)
        return res.json()

@app.put("/api/categories/{id}", dependencies=[Depends(verify_admin)])
async def edit_category(id: int, data: Dict[Any, Any]):
    async with httpx.AsyncClient() as client:
        res = await client.patch(
            f"{SUPABASE_REST_URL}/categories?id=eq.{id}",
            headers=SUPABASE_HEADERS,
            json=data
        )
        return res.json()

@app.delete("/api/categories/{id}", dependencies=[Depends(verify_admin)])
async def delete_category(id: int):
    async with httpx.AsyncClient() as client:
        await client.delete(f"{SUPABASE_REST_URL}/categories?id=eq.{id}", headers=SUPABASE_HEADERS)
    return {"status": "success"}

@app.get("/api/orders", dependencies=[Depends(verify_admin)])
async def list_orders():
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{SUPABASE_REST_URL}/orders?select=*&order=created_at.desc", headers=SUPABASE_HEADERS)
        return res.json()

@app.put("/api/orders/{id}", dependencies=[Depends(verify_admin)])
async def update_order_status(id: int, data: Dict[Any, Any]):
    async with httpx.AsyncClient() as client:
        res = await client.patch(
            f"{SUPABASE_REST_URL}/orders?id=eq.{id}",
            headers=SUPABASE_HEADERS,
            json=data
        )
        return res.json()

@app.get("/api/settings")
async def get_settings():
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{SUPABASE_REST_URL}/settings?limit=1", headers=SUPABASE_HEADERS)
            data = res.json()
            return data[0] if data else {}
    except:
        return {}

@app.post("/api/settings", dependencies=[Depends(verify_admin)])
async def save_settings(data: Dict[Any, Any]):
    async with httpx.AsyncClient() as client:
        exist_res = await client.get(f"{SUPABASE_REST_URL}/settings?limit=1", headers=SUPABASE_HEADERS)
        exist = exist_res.json()
        if exist:
            res = await client.patch(
                f"{SUPABASE_REST_URL}/settings?id=eq.{exist[0]['id']}",
                headers=SUPABASE_HEADERS,
                json=data
            )
        else:
            res = await client.post(f"{SUPABASE_REST_URL}/settings", headers=SUPABASE_HEADERS, json=data)
        return res.json()

# --- STATIC FILES ---

@app.get("/logo.jpg")
async def get_logo():
    if os.path.exists("logo.jpg"):
        return FileResponse("logo.jpg")
    raise HTTPException(status_code=404)

@app.get("/")
async def read_index():
    return FileResponse("index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
