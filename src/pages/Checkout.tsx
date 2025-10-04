import React, { useState } from "react";
import StripePayment from "../components/StripePayment";
import PayPalPayment from "../components/PayPalPayment";
import { useAppSelector, useAppDispatch } from "../store/hooks";
import { clearCart } from "../store/slices/cartSlice";

const Checkout: React.FC = () => {
  const cart = useAppSelector(state => state.cart.items);
  const dispatch = useAppDispatch();
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");

  const handleSuccess = () => {
    dispatch(clearCart());
    setConfirmation("Order confirmed! An invoice has been sent to your email.");
    setError("");
  };

  const handleFailure = () => {
    setConfirmation("");
    setError("Payment failed. Please try again.");
  };

  return (
    <div className="p-6 max-w-lg mx-auto">
      <h1 className="text-2xl font-bold mb-4">Checkout</h1>
      {confirmation && <p className="text-green-600">{confirmation}</p>}
      {error && <p className="text-red-600">{error}</p>}
      {cart.length > 0 && (
        <>
          <StripePayment onSuccess={handleSuccess} onFailure={handleFailure} />
          <PayPalPayment onSuccess={handleSuccess} onFailure={handleFailure} />
        </>
      )}
    </div>
  );
};

export default Checkout;