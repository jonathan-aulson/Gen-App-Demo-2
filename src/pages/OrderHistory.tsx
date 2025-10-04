import React, { useEffect, useState } from "react";
import { fetchUserOrders, generateInvoice, Order } from "../services/orderService";

const OrderHistory: React.FC = () => {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadOrders = async () => {
      setLoading(true);
      const data = await fetchUserOrders();
      setOrders(data);
      setLoading(false);
    };
    loadOrders();
  }, []);

  if (loading) {
    return <p className="text-center text-gray-600 mt-8">Loading your orders...</p>;
  }

  if (orders.length === 0) {
    return (
      <div className="container mx-auto px-4 py-12 text-center">
        <h2 className="text-2xl font-bold text-navy-700 mb-4">Order History</h2>
        <p className="text-gray-600 mb-6">You haven’t placed any orders yet.</p>
        <a
          href="/catalog"
          className="btn-primary inline-block"
        >
          Browse Books
        </a>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h2 className="text-3xl font-bold text-navy-700 mb-6 text-center">Your Orders</h2>
      <div className="space-y-6">
        {orders.map((order) => (
          <div
            key={order.id}
            className="bg-white shadow-md rounded-lg p-6 border border-gray-100"
          >
            <div className="flex flex-col md:flex-row md:justify-between md:items-center mb-4">
              <div>
                <p className="text-sm text-gray-600">Order ID: {order.id}</p>
                <p className="text-sm text-gray-600">Date: {order.date}</p>
                <p
                  className={`text-sm font-semibold ${
                    order.status === "Delivered"
                      ? "text-green-600"
                      : order.status === "Processing"
                      ? "text-yellow-600"
                      : "text-blue-600"
                  }`}
                >
                  Status: {order.status}
                </p>
              </div>
              <p className="text-lg font-semibold text-navy-700 mt-2 md:mt-0">
                Total: ${order.total.toFixed(2)}
              </p>
            </div>

            <div className="border-t border-gray-200 pt-4 space-y-2">
              {order.items.map((item, idx) => (
                <div
                  key={idx}
                  className="flex justify-between text-sm text-gray-700"
                >
                  <span>
                    {item.title} (x{item.quantity})
                  </span>
                  <span>${(item.price * item.quantity).toFixed(2)}</span>
                </div>
              ))}
            </div>

            <div className="mt-4 flex justify-end">
              <button
                onClick={() => generateInvoice(order)}
                className="btn-secondary text-sm"
              >
                Download Invoice
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default OrderHistory;