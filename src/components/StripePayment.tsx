import React, { useEffect, useState } from "react";
import { loadStripe } from "@stripe/stripe-js";
import {
  Elements,
  CardElement,
  useStripe,
  useElements
} from "@stripe/react-stripe-js";
import { createPaymentIntent, verifyPayment } from "../services/paymentService";

const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || "");

interface StripeCheckoutProps {
  totalAmount: number;
  onSuccess: () => void;
  onFailure: () => void;
}

const CheckoutForm: React.FC<StripeCheckoutProps> = ({ totalAmount, onSuccess, onFailure }) => {
  const stripe = useStripe();
  const elements = useElements();
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const initializePayment = async () => {
      try {
        const { clientSecret } = await createPaymentIntent(totalAmount * 100);
        setClientSecret(clientSecret);
      } catch (err) {
        console.error(err);
        setError("Failed to initialize payment.");
      }
    };
    initializePayment();
  }, [totalAmount]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!stripe || !elements || !clientSecret) return;

    setLoading(true);
    setError("");

    const cardElement = elements.getElement(CardElement);
    if (!cardElement) return;

    const { paymentIntent, error } = await stripe.confirmCardPayment(clientSecret, {
      payment_method: {
        card: cardElement
      }
    });

    if (error) {
      setError(error.message || "Payment failed.");
      setLoading(false);
      onFailure();
    } else if (paymentIntent && paymentIntent.status === "succeeded") {
      await verifyPayment(paymentIntent.id);
      setLoading(false);
      onSuccess();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <label className="block text-gray-700 font-medium">Card Details</label>
      <div className="border rounded p-3">
        <CardElement options={{ style: { base: { fontSize: "16px" } } }} />
      </div>
      {error && <p className="text-red-600 text-sm">{error}</p>}
      <button
        type="submit"
        disabled={loading || !stripe}
        className="btn-primary w-full"
      >
        {loading ? "Processing..." : `Pay $${totalAmount.toFixed(2)}`}
      </button>
    </form>
  );
};

const StripePayment: React.FC<StripeCheckoutProps> = (props) => {
  return (
    <Elements stripe={stripePromise}>
      <CheckoutForm {...props} />
    </Elements>
  );
};

export default StripePayment;