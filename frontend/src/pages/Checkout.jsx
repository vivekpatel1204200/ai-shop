import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { loadStripe } from "@stripe/stripe-js";
import { Elements, CardElement, useStripe, useElements } from "@stripe/react-stripe-js";
import api from "../api";

const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY);

function PaymentForm({ clientSecret }) {
  const stripe = useStripe();
  const elements = useElements();
  const navigate = useNavigate();
  const [error, setError] = useState(null);
  const [processing, setProcessing] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!stripe || !elements) return;

    setProcessing(true);
    setError(null);

    const result = await stripe.confirmCardPayment(clientSecret, {
      payment_method: {
        card: elements.getElement(CardElement),
      },
    });

    if (result.error) {
      setError(result.error.message);
      setProcessing(false);
      return;
    }

    if (result.paymentIntent.status === "succeeded") {
      try {
        await api.post("/confirm-payment", {
          payment_intent_id: result.paymentIntent.id,
        });
        navigate("/orders");
      } catch (err) {
        setError(err.response?.data?.detail || "Order confirmation failed.");
      }
    }
    setProcessing(false);
  };

  return (
    <form onSubmit={handleSubmit}>
      <CardElement />
      <button type="submit" disabled={!stripe || processing}>
        {processing ? "Processing..." : "Pay Now"}
      </button>
      {error && <p>{error}</p>}
    </form>
  );
}

export default function Checkout() {
  const [clientSecret, setClientSecret] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.post("/create-payment-intent")
      .then((res) => setClientSecret(res.data.client_secret))
      .catch((err) => setError(err.response?.data?.detail || "Could not start payment."));
  }, []);

  if (error) return <p>{error}</p>;
  if (!clientSecret) return <p>Setting up payment...</p>;

  return (
    <div className="checkout-page">
      <h2>Checkout</h2>
      <Elements stripe={stripePromise}>
        <PaymentForm clientSecret={clientSecret} />
      </Elements>
    </div>
  );
}