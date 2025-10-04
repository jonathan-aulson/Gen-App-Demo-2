import api from "./api";

export interface OrderItem {
  bookId: string;
  title: string;
  quantity: number;
  price: number;
}

export interface Order {
  id: string;
  date: string;
  total: number;
  status: "Pending" | "Processing" | "Shipped" | "Delivered";
  items: OrderItem[];
}

export async function getUserOrders(): Promise<Order[]> {
  try {
    const response = await api.get("/orders");
    return response.data;
  } catch (error) {
    console.error("Failed to fetch orders:", error);
    throw error;
  }
}

export async function createOrder(order: Partial<Order>): Promise<Order> {
  try {
    const response = await api.post("/orders", order);
    return response.data;
  } catch (error) {
    console.error("Failed to create order:", error);
    throw error;
  }
}

export async function updateOrderStatus(id: string, status: string): Promise<Order> {
  try {
    const response = await api.put(`/orders/${id}`, { status });
    return response.data;
  } catch (error) {
    console.error("Failed to update order status:", error);
    throw error;
  }
}