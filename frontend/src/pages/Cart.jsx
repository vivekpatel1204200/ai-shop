import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";

export default function Cart() {
  const [items, setItems] = useState([]);
  const [products, setProducts] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const loadCart = async () => {
    setLoading(true);
    const cartRes = await api.get("/cart");
    setItems(cartRes.data);

    const productRes = await api.get("/products");
    const productMap = {};
    productRes.data.forEach((p) => { productMap[p.id] = p; });
    setProducts(productMap);
    setLoading(false);
  };

  useEffect(() => {
    loadCart();
  }, []);

  const handleUpdateQuantity = async (itemId, quantity) => {
    if (quantity < 1) return;
    await api.put(`/cart/${itemId}?quantity=${quantity}`);
    loadCart();
  };

  const handleRemove = async (itemId) => {
    await api.delete(`/cart/${itemId}`);
    loadCart();
  };

   const handleCheckout = () => {
    navigate("/checkout");
  };

  const total = items.reduce((sum, item) => {
    const product = products[item.product_id];
    return sum + (product ? product.price * item.quantity : 0);
  }, 0);

  if (loading) return <p>Loading your cart...</p>;
  if (items.length === 0) return <p>Your cart is empty.</p>;

  return (
    <div className="cart-page">
      <h2>Your Cart</h2>
      {items.map((item) => {
        const product = products[item.product_id];
        return (
          <div key={item.id} className="cart-item">
            <span>{product ? product.name : "Loading..."}</span>
            <span>₹{product ? product.price : "-"}</span>
            <button onClick={() => handleUpdateQuantity(item.id, item.quantity - 1)}>-</button>
            <span>{item.quantity}</span>
            <button onClick={() => handleUpdateQuantity(item.id, item.quantity + 1)}>+</button>
            <button onClick={() => handleRemove(item.id)}>Remove</button>
          </div>
        );
      })}
      <h3>Total: ₹{total}</h3>
      <button onClick={handleCheckout}>Checkout</button>
      {error && <p>{error}</p>}
    </div>
  );
}