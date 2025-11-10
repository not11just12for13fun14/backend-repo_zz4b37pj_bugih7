import os
import uuid
from typing import Optional, List
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException, Header, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from jose import jwt, JWTError
from passlib.context import CryptContext
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Product, Category, Order, AuthUser, WalletTopup, WalletPayment

APP_TITLE = "GreenFood API"
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title=APP_TITLE)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure uploads directory exists and is served
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Auth helpers

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_user_by_email(email: str) -> Optional[dict]:
    return db["authuser"].find_one({"email": email})


def get_current_user(authorization: Optional[str] = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = get_user_by_email(sub)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_admin(user: dict):
    if (user.get("role") or "").lower() != "admin":
        raise HTTPException(status_code=403, detail="Admin only")


@app.get("/")
def read_root():
    return {"message": f"{APP_TITLE} is running"}


@app.get("/schema")
def get_schema():
    return {"collections": ["authuser", "category", "product", "order", "wallettopup", "setting"]}


# ---------- Auth Endpoints ----------
@app.post("/auth/register")
def register_user(name: str = Form(...), email: str = Form(...), password: str = Form(...)):
    if db["authuser"].find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    # Always user role; admin will be set manually in DB
    doc = AuthUser(email=email, name=name, password_hash=hash_password(password), role="user", balance=0, is_active=True).model_dump()
    doc["created_at"] = datetime.now(timezone.utc)
    doc["updated_at"] = datetime.now(timezone.utc)
    res = db["authuser"].insert_one(doc)
    return {"_id": str(res.inserted_id), "email": email, "role": "user"}


@app.post("/auth/login")
def login(email: str = Form(...), password: str = Form(...)):
    user = get_user_by_email(email)
    if not user or not verify_password(password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Email atau password salah")
    token = create_access_token({"sub": user["email"], "role": user.get("role", "user")})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "email": user["email"],
            "name": user.get("name"),
            "role": user.get("role", "user"),
            "balance": int(user.get("balance", 0)),
        },
    }


@app.get("/me")
def me(user: dict = Depends(get_current_user)):
    return {
        "email": user["email"],
        "name": user.get("name"),
        "role": user.get("role", "user"),
        "balance": int(user.get("balance", 0)),
    }


# ---------- Settings (QRIS) ----------
@app.get("/settings/qris")
def get_qris():
    s = db["setting"].find_one({"key": "qris"})
    if not s:
        return {"image": None}
    return {"image": s.get("image")}


@app.post("/settings/qris")
def set_qris(image: UploadFile = File(...), user: dict = Depends(get_current_user)):
    require_admin(user)
    try:
        ext = os.path.splitext(image.filename or "")[1] or ".png"
        fname = f"qris-{uuid.uuid4().hex}{ext}"
        dest_path = os.path.join(UPLOAD_DIR, fname)
        with open(dest_path, "wb") as f:
            f.write(image.file.read())
        image_url = f"/uploads/{fname}"
        db["setting"].update_one({"key": "qris"}, {"$set": {"image": image_url, "updated_at": datetime.now(timezone.utc)}}, upsert=True)
        return {"image": image_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Category ----------
@app.get("/categories")
def list_categories():
    try:
        cats = get_documents("category")
        for c in cats:
            c["_id"] = str(c["_id"])
        return cats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/categories")
def create_category(category: Category, user: dict = Depends(get_current_user)):
    require_admin(user)
    try:
        inserted_id = create_document("category", category)
        return {"_id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Products ----------
@app.get("/products")
def list_products(category: Optional[str] = None, q: Optional[str] = None):
    try:
        query = {}
        if category:
            query["category"] = category
        if q:
            query["title"] = {"$regex": q, "$options": "i"}
        prods = get_documents("product", query, limit=100)
        for p in prods:
            p["_id"] = str(p["_id"])
        return prods
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/products")
def create_product(
    user: dict = Depends(get_current_user),
    title: str = Form(...),
    price: float = Form(...),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    in_stock: Optional[bool] = Form(True),
    image: Optional[UploadFile] = File(None),
):
    require_admin(user)
    try:
        image_url = None
        if image is not None:
            ext = os.path.splitext(image.filename or "")[1] or ".jpg"
            fname = f"{uuid.uuid4().hex}{ext}"
            dest_path = os.path.join(UPLOAD_DIR, fname)
            with open(dest_path, "wb") as f:
                f.write(image.file.read())
            image_url = f"/uploads/{fname}"
        payload = {
            "title": title,
            "price": price,
            "description": description,
            "category": category,
            "in_stock": bool(in_stock) if in_stock is not None else True,
            "image": image_url,
        }
        inserted_id = create_document("product", payload)
        return {"_id": inserted_id, "image": image_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Orders ----------
@app.post("/orders")
def create_order(order: Order, authorization: Optional[str] = Header(default=None)):
    try:
        buyer = None
        if authorization:
            try:
                buyer = get_current_user(authorization)
            except Exception:
                buyer = None
        # If paying with GreenPay balance, require sufficient balance and deduct immediately
        if order.payment_method == "greenpay" and buyer:
            total = int(order.total)
            current = int(buyer.get("balance", 0))
            if current < total:
                raise HTTPException(status_code=400, detail="Saldo GreenPay tidak cukup")
            db["authuser"].update_one({"_id": buyer["_id"]}, {"$inc": {"balance": -total}, "$set": {"updated_at": datetime.now(timezone.utc)}})
            order.status = "paid"
        doc = order.model_dump()
        if buyer:
            doc["buyer_id"] = str(buyer["_id"])
        inserted_id = create_document("order", doc)
        return {"_id": inserted_id, "status": doc.get("status", "received")}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Wallet (GreenPay) Topup with QRIS proof ----------
@app.post("/wallet/topup-request")
def wallet_topup_request(amount: int = Form(...), proof: UploadFile = File(...), user: dict = Depends(get_current_user)):
    try:
        amount = int(amount)
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Jumlah top up tidak valid")
        ext = os.path.splitext(proof.filename or "")[1] or ".jpg"
        fname = f"topup-{uuid.uuid4().hex}{ext}"
        dest_path = os.path.join(UPLOAD_DIR, fname)
        with open(dest_path, "wb") as f:
            f.write(proof.file.read())
        proof_url = f"/uploads/{fname}"
        doc = {
            "user_id": str(user["_id"]),
            "email": user.get("email"),
            "amount": amount,
            "proof": proof_url,
            "status": "pending",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        res_id = db["wallettopup"].insert_one(doc).inserted_id
        return {"_id": str(res_id), "status": "pending"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/topup-requests")
def list_topup_requests(status: Optional[str] = None, user: dict = Depends(get_current_user)):
    require_admin(user)
    q = {}
    if status:
        q["status"] = status
    rows = list(db["wallettopup"].find(q).sort("created_at", -1))
    for r in rows:
        r["_id"] = str(r["_id"])
    return rows


@app.post("/admin/topup-requests/{req_id}/approve")
def approve_topup(req_id: str, user: dict = Depends(get_current_user)):
    require_admin(user)
    req = db["wallettopup"].find_one({"_id": ObjectId(req_id)})
    if not req:
        raise HTTPException(status_code=404, detail="Topup request not found")
    if req.get("status") == "approved":
        return {"status": "already_approved"}
    uid = req.get("user_id")
    amount = int(req.get("amount", 0))
    # credit balance
    db["authuser"].update_one({"_id": ObjectId(uid)}, {"$inc": {"balance": amount}, "$set": {"updated_at": datetime.now(timezone.utc)}})
    db["wallettopup"].update_one({"_id": ObjectId(req_id)}, {"$set": {"status": "approved", "updated_at": datetime.now(timezone.utc)}})
    return {"status": "approved"}


@app.post("/admin/topup-requests/{req_id}/reject")
def reject_topup(req_id: str, user: dict = Depends(get_current_user)):
    require_admin(user)
    req = db["wallettopup"].find_one({"_id": ObjectId(req_id)})
    if not req:
        raise HTTPException(status_code=404, detail="Topup request not found")
    db["wallettopup"].update_one({"_id": ObjectId(req_id)}, {"$set": {"status": "rejected", "updated_at": datetime.now(timezone.utc)}})
    return {"status": "rejected"}


@app.get("/wallet")
def wallet_balance(user: dict = Depends(get_current_user)):
    fresh = get_user_by_email(user["email"]) or user
    return {"balance": int(fresh.get("balance", 0))}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
