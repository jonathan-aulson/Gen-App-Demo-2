import React, { useState } from "react";
import { useAppSelector, useAppDispatch } from "../store/hooks";
import { removeFromCart, updateQuantity, clearCart } from "../store/slices/cartSlice";
import { useNavigate } from "react-router-dom";

const Cart: React.FC = () => {
  const cart = useAppSelector(state => state.cart.items);
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const [discountCode, setDiscountCode] = useState("");
  const [discount, setDiscount] = useState(0);
  const [error, setError] = useState("");

  const handleQuantityChange = (id: string, qty: number) => {
    dispatch(updateQuantity({ id, quantity: qty }));
  };

  const handleApplyDiscount = () => {
    if (discountCode.trim().toUpperCase() === "SAVE10") {
      setDiscount(0.1);
      setError("");
    } else {
      setDiscount(0);
      setError("Invalid discount code");
    }
  };

  const subtotal = cart.reduce((acc, item) => acc + item.price * item.quantity, 0);
  const total = subtotal - subtotal * discount;

  const handleCheckout = () => {
    navigate("/checkout");
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold mb-4">Shopping Cart</h1>
      {cart.length === 0 ? (
        <p>Your cart is empty</p>
      ) : (
        <>
          {cart.map(item => (
            <div key={item.id} className="flex justify-between border-b py-2">
              <div>
                <p>{item.title}</p>
                <p>${item.price}</p>
              </div>
              <div>
                <input
                  type="number"
                  value={item.quantity}
                  min="1"
                  onChange={e => handleQuantityChange(item.id, parseInt(e.target.value))}
                  className="border p-1 w-16"
                />
                <button
                  onClick={() => dispatch(removeFromCart(item.id))}
                  className="ml-2 text-red-600"
                >
                  Remove
                </button>
              </div>
            </div>
          ))}
          <div className="mt-4">
            <input
              placeholder="Discount code"
              value={discountCode}
              onChange={e => setDiscountCode(e.target.value)}
              className="border p-2 rounded"
            />
            <button
              onClick={handleApplyDiscount}
              className="ml-2 bg-blue-600 text-white p-2 rounded"
            >
              Apply
            </button>
            {error && <p className="text-red-600">{error}</p>}
          </div>
          <div className="mt-4">
            <p>Subtotal: ${subtotal.toFixed(2)}</p>
            {discount > 0 && <p>Discount: {(discount * 100).toFixed(0)}%</p>}
            <p>Total: ${total.toFixed(2)}</p>
          </div>
          <button
            onClick={handleCheckout}
            className="mt-4 bg-green-600 text-white p-2 rounded"
          >
            Proceed to Checkout
          </button>
        </>
      )}
    </div>
  );
};

export default Cart;