import api from "../api";

export default function ProductCard({ product }) {
  const handleAddToCart = async () => {
    try {
      await api.post("/cart", { product_id: product.id, quantity: 1 });
      alert("Added to cart!");
    } catch (err) {
      alert(err.response?.data?.detail || "Could not add to cart.");
    }
  };

  return (
    <div className="product-card">
      <img src={product.image_url || "https://via.placeholder.com/150"} alt={product.name} />
      <h3>{product.name}</h3>
      <p>{product.category}</p>
      <p>₹{product.price}</p>
      <p>{product.stock > 0 ? `${product.stock} in stock` : "Out of stock"}</p>
      {product.stock > 0 && <button onClick={handleAddToCart}>Add to Cart</button>}
    </div>
  );
}