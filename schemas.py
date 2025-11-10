"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List

class AuthUser(BaseModel):
    email: EmailStr
    name: str
    password_hash: str
    role: str = Field("user", description="user | admin")
    balance: int = Field(0, ge=0, description="GreenPay wallet balance in IDR")
    is_active: bool = True

class Category(BaseModel):
    name: str = Field(..., description="Category display name")
    slug: str = Field(..., description="URL-friendly unique slug")
    icon: Optional[str] = Field(None, description="Optional icon name")

class Product(BaseModel):
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in rupiah")
    category: str = Field(..., description="Product category slug")
    in_stock: bool = Field(True, description="Whether product is in stock")
    image: Optional[str] = Field(None, description="Stored image path or data URI")
    rating: Optional[float] = Field(4.5, ge=0, le=5, description="Average rating")

class OrderItem(BaseModel):
    product_id: str
    title: str
    price: float
    quantity: int = Field(..., ge=1)
    image: Optional[str] = None

class Order(BaseModel):
    buyer_id: Optional[str] = None
    buyer_name: str
    buyer_email: str
    buyer_address: str
    items: List[OrderItem]
    subtotal: float
    discount: float = Field(0, ge=0)
    delivery_fee: float
    total: float
    status: str = Field("pending")
    coupon_code: Optional[str] = None
    payment_method: Optional[str] = None

class WalletTopup(BaseModel):
    amount: int = Field(..., ge=1000, description="Top up amount in IDR")
    via: str = Field("qris", description="Top up method: qris")

class WalletPayment(BaseModel):
    amount: int = Field(..., ge=1)
    description: Optional[str] = None

