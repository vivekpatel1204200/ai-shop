import { useEffect, useState } from "react";
import api from "../api";

export default function Orders() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/orders")
      .then((res) => setOrders(res.data))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p>Loading your orders...</p>;
  if (orders.length === 0) return <p>You have no past orders.</p>;

  return (
    <div className="orders-page">
      <h2>Your Orders</h2>
      {orders.map((order) => (
        <div key={order.id} className="order-card">
          <h4>Order #{order.id} — ₹{order.total_amount} — {order.status}</h4>
          <p>Payment: {order.payment_status}</p>
          <ul>
            {order.items.map((item, idx) => (
              <li key={idx}>Product #{item.product_id} × {item.quantity} — ₹{item.price}</li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}