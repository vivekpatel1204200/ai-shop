from pydantic import BaseModel, ConfigDict
from typing import Optional

class ProductBase(BaseModel):
    name: str
    category: str
    description: Optional[str] = None
    price: float
    stock: int = 0
    image_url: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    image_url: Optional[str] = None

class ProductOut(ProductBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class UserCreate(BaseModel):
    name: str
    email: str
    password: str

class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str


class CartItemCreate(BaseModel):
    product_id: int
    quantity: int = 1

class CartItemOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    model_config = ConfigDict(from_attributes=True)

class OrderItemOut(BaseModel):
    product_id: int
    quantity: int
    price: float
    model_config = ConfigDict(from_attributes=True)

class OrderOut(BaseModel):
    id: int
    total_amount: float
    status: str
    payment_status: str
    items: list[OrderItemOut] = []
    model_config = ConfigDict(from_attributes=True)

class PaymentIntentOut(BaseModel):
    client_secret: str

class ConfirmPaymentIn(BaseModel):
    payment_intent_id: str



class ChatOut(BaseModel):
    response: str

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatIn(BaseModel):
    message: str
    history: list[ChatMessage] = []