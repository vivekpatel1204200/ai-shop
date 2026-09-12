import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Navbar() {
  const { token, user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <nav className="navbar">
      <Link to="/">AI Shop</Link>
      <div>
       {token ? (
  <>
    <Link to="/cart">Cart</Link>
    <Link to="/orders">Orders</Link>
    <Link to="/assistant">Assistant</Link>
    {user?.role === "admin" && <Link to="/admin">Admin</Link>}
    <button onClick={handleLogout}>Logout</button>
  </>
) : (
          <>
            <Link to="/login">Login</Link>
            <Link to="/register">Register</Link>
          </>
        )}
      </div>
    </nav>
  );
}