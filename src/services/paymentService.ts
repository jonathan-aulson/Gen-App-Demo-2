import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "https://api.bookhaven.com";

export interface PaymentIntentResponse {
  clientSecret: string;
}

export async function createPaymentIntent(amount: number): Promise<PaymentIntentResponse> {
  try {
    const response = await axios.post(`${API_BASE}/payments/create-intent`, { amount });
    return response.data;
  } catch (error) {
    console.error("Error creating payment intent:", error);
    throw error;
  }
}

export async function verifyPayment(paymentId: string): Promise<{ success: boolean }> {
  try {
    const response = await axios.post(`${API_BASE}/payments/verify`, { paymentId });
    return response.data;
  } catch (error) {
    console.error("Error verifying payment:", error);
    throw error;
  }
}