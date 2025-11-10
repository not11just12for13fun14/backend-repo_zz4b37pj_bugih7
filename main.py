import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Product, Category, Order

app = FastAPI(title="Supermarket API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProductIn(Product):
    pass

class OrderIn(Order):
    pass

@app.get("/")
def read_root():
    return {"message": "Supermarket API is running"}

@app.get("/schema")
def get_schema():
    # Expose schemas to the built-in DB viewer
    return {
        "collections": [
            "user",
            "category",
            "product",
            "order",
        ]
    }

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
def create_category(category: Category):
    try:
        inserted_id = create_document("category", category)
        return {"_id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
def create_product(product: ProductIn):
    try:
        inserted_id = create_document("product", product)
        return {"_id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/orders")
def create_order(order: OrderIn):
    try:
        inserted_id = create_document("order", order)
        return {"_id": inserted_id, "status": "received"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
