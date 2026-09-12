import os
from typing import TypedDict, List
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

import models

llm = ChatGroq(model="openai/gpt-oss-120b", groq_api_key=os.getenv("GROQ_API_KEY"))


class AssistantState(TypedDict):
    question: str
    history: List[dict]
    user_id: int
    intent: str
    search_term: str
    products: List[dict]
    orders: List[dict]
    answer: str
    cart_items: List[dict]


def format_history(history: List[dict]) -> str:
    if not history:
        return "(no previous messages)"
    lines = []
    for msg in history[-6:]:
        speaker = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{speaker}: {msg['content']}")
    return "\n".join(lines)


def classify_intent(state: AssistantState) -> AssistantState:
    history_text = format_history(state["history"])
    prompt = f"""You are a shopping assistant. Recent conversation:

{history_text}

The user just said: "{state['question']}"

Classify this message into exactly ONE of these categories, using the conversation for context:
- PRODUCT: asking about products, searching, or shopping recommendations
- ORDER: asking about their own past orders, order status, or purchase history
- CART: asking what's in their cart, or about their current cart contents
- GENERAL: greetings, small talk, or anything else

Reply with ONLY one word: PRODUCT, ORDER, CART, or GENERAL."""
    response = llm.invoke(prompt)
    state["intent"] = response.content.strip().upper()
    return state


def route_by_intent(state: AssistantState) -> str:
    if state["intent"] == "PRODUCT":
        return "understand_query"
    elif state["intent"] == "ORDER":
        return "fetch_orders"
    elif state["intent"] == "CART":
        return "fetch_cart"
    else:
        return "generate_general_answer"


def understand_query(state: AssistantState) -> AssistantState:
    history_text = format_history(state["history"])
    prompt = f"""Recent conversation:

{history_text}

The user just said: "{state['question']}"

Extract a single short keyword or category to search a product database, using the conversation for context if needed. Reply with ONLY the keyword, nothing else."""
    response = llm.invoke(prompt)
    state["search_term"] = response.content.strip()
    return state


def search_products(state: AssistantState, db: Session) -> AssistantState:
    term = f"%{state['search_term']}%"
    results = db.query(models.Product).filter(
        (models.Product.name.ilike(term)) | (models.Product.category.ilike(term))
    ).all()
    state["products"] = [
        {"name": p.name, "category": p.category, "price": p.price, "stock": p.stock}
        for p in results
    ]
    return state


def fetch_orders(state: AssistantState, db: Session) -> AssistantState:
    orders = db.query(models.Order).filter(models.Order.user_id == state["user_id"]).all()
    order_data = []
    for o in orders:
        items = []
        for item in o.items:
            product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
            items.append({
                "product_name": product.name if product else f"Product #{item.product_id}",
                "quantity": item.quantity,
                "price": item.price,
            })
        order_data.append({
            "id": o.id,
            "total_amount": o.total_amount,
            "status": o.status,
            "payment_status": o.payment_status,
            "items": items,
        })
    state["orders"] = order_data
    return state

def fetch_cart(state: AssistantState, db: Session) -> AssistantState:
    items = db.query(models.CartItem).filter(models.CartItem.user_id == state["user_id"]).all()
    cart_data = []
    for item in items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        cart_data.append({
            "product_name": product.name if product else f"Product #{item.product_id}",
            "quantity": item.quantity,
            "price": product.price if product else None,
        })
    state["cart_items"] = cart_data
    return state


def generate_product_answer(state: AssistantState) -> AssistantState:
    if not state["products"]:
        state["answer"] = f"I couldn't find any products matching '{state['search_term']}'. Try browsing our full catalog instead."
        return state

    product_list = "\n".join(
        f"- {p['name']} ({p['category']}) — ₹{p['price']}, {p['stock']} in stock"
        for p in state["products"]
    )
    prompt = f"""You are a helpful shopping assistant. The user asked: "{state['question']}"

Matching products found:
{product_list}

Write a short, friendly response recommending these products."""
    response = llm.invoke(prompt)
    state["answer"] = response.content
    return state


def generate_order_answer(state: AssistantState) -> AssistantState:
    if not state["orders"]:
        state["answer"] = "You don't have any past orders yet."
        return state

    order_text = "\n\n".join(
        f"Order #{o['id']} — ₹{o['total_amount']} — {o['status']} — Payment: {o['payment_status']}\n"
        + "\n".join(f"  - {i['product_name']} x{i['quantity']} @ ₹{i['price']}" for i in o["items"])
        for o in state["orders"]
    )
    prompt = f"""You are a shopping assistant. The user asked: "{state['question']}"

Here is their REAL order history from our database — use ONLY this data, do not invent any details:

{order_text}

Write a short, friendly summary answering their question using only the data above."""
    response = llm.invoke(prompt)
    state["answer"] = response.content
    return state

def generate_cart_answer(state: AssistantState) -> AssistantState:
    if not state["cart_items"]:
        state["answer"] = "Your cart is currently empty."
        return state

    cart_text = "\n".join(
        f"- {i['product_name']} x{i['quantity']} @ ₹{i['price']}"
        for i in state["cart_items"]
    )
    prompt = f"""You are a shopping assistant. The user asked: "{state['question']}"

Here is their REAL current cart contents — use ONLY this data, do not invent anything:

{cart_text}

Write a short, friendly summary of what's in their cart."""
    response = llm.invoke(prompt)
    state["answer"] = response.content
    return state


def generate_general_answer(state: AssistantState) -> AssistantState:
    history_text = format_history(state["history"])
    prompt = f"""You are a friendly shopping assistant for an online store. Recent conversation:

{history_text}

Respond naturally and briefly to: "{state['question']}"

IMPORTANT: Never invent or guess specific facts (like order numbers, prices, delivery dates, or product details) that were not explicitly given to you. If you don't have real data for something, say so honestly instead of making something up."""
    response = llm.invoke(prompt)
    state["answer"] = response.content
    return state


def build_graph(db: Session):
    graph = StateGraph(AssistantState)

    graph.add_node("classify_intent", classify_intent)
    graph.add_node("understand_query", understand_query)
    graph.add_node("search_products", lambda state: search_products(state, db))
    graph.add_node("fetch_orders", lambda state: fetch_orders(state, db))
    graph.add_node("fetch_cart", lambda state: fetch_cart(state, db))
    graph.add_node("generate_product_answer", generate_product_answer)
    graph.add_node("generate_order_answer", generate_order_answer)
    graph.add_node("generate_cart_answer", generate_cart_answer)
    graph.add_node("generate_general_answer", generate_general_answer)

    graph.set_entry_point("classify_intent")

    graph.add_conditional_edges("classify_intent", route_by_intent, {
        "understand_query": "understand_query",
        "fetch_orders": "fetch_orders",
        "fetch_cart": "fetch_cart",
        "generate_general_answer": "generate_general_answer",
    })

    graph.add_edge("understand_query", "search_products")
    graph.add_edge("search_products", "generate_product_answer")
    graph.add_edge("generate_product_answer", END)

    graph.add_edge("fetch_orders", "generate_order_answer")
    graph.add_edge("generate_order_answer", END)

    graph.add_edge("fetch_cart", "generate_cart_answer")
    graph.add_edge("generate_cart_answer", END)

    graph.add_edge("generate_general_answer", END)

    return graph.compile()


def run_assistant(question: str, history: List[dict], user_id: int, db: Session) -> str:
    graph = build_graph(db)
    result = graph.invoke({
        "question": question,
        "history": history,
        "user_id": user_id,
        "intent": "",
        "search_term": "",
        "products": [],
        "orders": [],
        "cart_items": [],
        "answer": "",
    })
    return result["answer"]