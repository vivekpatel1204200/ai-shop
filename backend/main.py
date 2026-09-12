from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
import auth
from typing import List
from typing import List
import stripe
import os
import ai


import models, schemas
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

app = FastAPI(title="AI Shop API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/products", response_model=schemas.ProductOut)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db), admin: models.User = Depends(auth.require_admin)):
    db_product = models.Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@app.get("/products", response_model=List[schemas.ProductOut])
def list_products(db: Session = Depends(get_db)):
    return db.query(models.Product).all()

@app.get("/products/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.put("/products/{product_id}", response_model=schemas.ProductOut)
def update_product(product_id: int, updates: schemas.ProductUpdate, db: Session = Depends(get_db), admin: models.User = Depends(auth.require_admin)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product

@app.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db), admin: models.User = Depends(auth.require_admin)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return {"message": "Product deleted"}

@app.post("/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = models.User(
        name=user.name,
        email=user.email,
        password=auth.hash_password(user.password),
        role="user"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = auth.create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/users", response_model=List[schemas.UserOut])
def list_users(db: Session = Depends(get_db), admin: models.User = Depends(auth.require_admin)):
    return db.query(models.User).all()

@app.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

@app.post("/cart", response_model=schemas.CartItemOut)
def add_to_cart(item: schemas.CartItemCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    existing = db.query(models.CartItem).filter(
        models.CartItem.user_id == current_user.id,
        models.CartItem.product_id == item.product_id
    ).first()

    if existing:
        existing.quantity += item.quantity
        db.commit()
        db.refresh(existing)
        return existing

    new_item = models.CartItem(user_id=current_user.id, product_id=item.product_id, quantity=item.quantity)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

@app.get("/cart", response_model=List[schemas.CartItemOut])
def view_cart(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id).all()

@app.put("/cart/{item_id}", response_model=schemas.CartItemOut)
def update_cart_item(item_id: int, quantity: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    item = db.query(models.CartItem).filter(
        models.CartItem.id == item_id,
        models.CartItem.user_id == current_user.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    item.quantity = quantity
    db.commit()
    db.refresh(item)
    return item

@app.delete("/cart/{item_id}")
def remove_cart_item(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    item = db.query(models.CartItem).filter(
        models.CartItem.id == item_id,
        models.CartItem.user_id == current_user.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    db.delete(item)
    db.commit()
    return {"message": "Item removed from cart"}

@app.post("/checkout", response_model=schemas.OrderOut)
def checkout(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    cart_items = db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id).all()

    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    total = 0
    order_items_data = []

    for item in cart_items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=400, detail=f"Product {item.product_id} no longer exists")
        line_total = product.price * item.quantity
        total += line_total
        order_items_data.append((product.id, item.quantity, product.price))

    new_order = models.Order(user_id=current_user.id, total_amount=total)
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    for product_id, quantity, price in order_items_data:
        db.add(models.OrderItem(order_id=new_order.id, product_id=product_id, quantity=quantity, price=price))

    for item in cart_items:
        db.delete(item)

    db.commit()
    db.refresh(new_order)
    return new_order

@app.get("/orders", response_model=List[schemas.OrderOut])
def list_orders(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.Order).filter(models.Order.user_id == current_user.id).all()

@app.post("/create-payment-intent", response_model=schemas.PaymentIntentOut)
def create_payment_intent(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    cart_items = db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id).all()
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    total = 0
    for item in cart_items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=400, detail=f"Product {item.product_id} no longer exists")
        total += product.price * item.quantity

    amount_in_cents = int(total * 100)

    intent = stripe.PaymentIntent.create(
        amount=amount_in_cents,
        currency="usd",
        metadata={"user_id": str(current_user.id)},
    )

    return {"client_secret": intent.client_secret}


@app.post("/confirm-payment", response_model=schemas.OrderOut)
def confirm_payment(payload: schemas.ConfirmPaymentIn, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    intent = stripe.PaymentIntent.retrieve(payload.payment_intent_id)

    if intent.status != "succeeded":
        raise HTTPException(status_code=400, detail="Payment not completed")

    cart_items = db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id).all()
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    total = 0
    order_items_data = []
    for item in cart_items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=400, detail=f"Product {item.product_id} no longer exists")
        total += product.price * item.quantity
        order_items_data.append((product.id, item.quantity, product.price))

    new_order = models.Order(user_id=current_user.id, total_amount=total, payment_status="paid")
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    for product_id, quantity, price in order_items_data:
        db.add(models.OrderItem(order_id=new_order.id, product_id=product_id, quantity=quantity, price=price))

    for item in cart_items:
        db.delete(item)

    db.commit()
    db.refresh(new_order)
    return new_order

@app.post("/ai/chat", response_model=schemas.ChatOut)
def ai_chat(payload: schemas.ChatIn, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    history = [{"role": m.role, "content": m.content} for m in payload.history]
    answer = ai.run_assistant(payload.message, history, current_user.id, db)
    return {"response": answer}