import axios, { AxiosError } from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "https://api.bookhaven.com",
  headers: {
    "Content-Type": "application/json"
  },
  withCredentials: true
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const message =
      error.response?.data && typeof error.response.data === "object"
        ? (error.response.data as any).message
        : error.message;
    console.error("API Error:", message);
    return Promise.reject(error);
  }
);

export default api;