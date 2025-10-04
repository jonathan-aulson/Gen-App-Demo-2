import api from "./api";

export interface Review {
  id: string;
  user: string;
  rating: number;
  comment: string;
  approved: boolean;
}

export async function getReviews(bookId: string): Promise<Review[]> {
  try {
    const response = await api.get(`/books/${bookId}/reviews`);
    return response.data;
  } catch (error) {
    console.error("Failed to fetch reviews:", error);
    throw error;
  }
}

export async function addReview(bookId: string, review: Omit<Review, "id" | "approved">): Promise<Review> {
  try {
    const response = await api.post(`/books/${bookId}/reviews`, review);
    return response.data;
  } catch (error) {
    console.error("Failed to add review:", error);
    throw error;
  }
}