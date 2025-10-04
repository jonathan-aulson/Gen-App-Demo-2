export interface Review {
  id: string;
  user: string;
  rating: number;
  comment: string;
  approved: boolean;
}

let mockReviews: Review[] = [
  { id: "1", user: "Alice", rating: 5, comment: "Fantastic read!", approved: true },
  { id: "2", user: "Bob", rating: 4, comment: "Enjoyed it a lot.", approved: true }
];

export async function fetchReviews(bookId: string): Promise<Review[]> {
  // Simulated API fetch
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(mockReviews.filter((r) => r.approved));
    }, 500);
  });
}

export async function submitReview(
  bookId: string,
  newReview: Omit<Review, "id" | "approved">
): Promise<Review> {
  // Simulate admin moderation
  return new Promise((resolve) => {
    setTimeout(() => {
      const review: Review = {
        id: String(Date.now()),
        approved: false, // Needs admin approval
        ...newReview
      };
      mockReviews.push(review);
      resolve(review);
    }, 700);
  });
}

export function approveReview(reviewId: string): void {
  mockReviews = mockReviews.map((r) =>
    r.id === reviewId ? { ...r, approved: true } : r
  );
}