import React, { useEffect, useState } from "react";
import StarRating from "./StarRating";
import { fetchReviews, submitReview, Review } from "../services/reviewService";
import { useAppSelector } from "../store/hooks";

interface ReviewSectionProps {
  bookId: string;
}

const ReviewSection: React.FC<ReviewSectionProps> = ({ bookId }) => {
  const user = useAppSelector((state) => state.user);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [newComment, setNewComment] = useState("");
  const [newRating, setNewRating] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    const loadReviews = async () => {
      const data = await fetchReviews(bookId);
      setReviews(data);
    };
    loadReviews();
  }, [bookId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user.token) {
      setMessage("You must be logged in to leave a review.");
      return;
    }
    if (newRating === 0 || newComment.trim() === "") {
      setMessage("Please provide both a rating and a comment.");
      return;
    }

    setSubmitting(true);
    const review = await submitReview(bookId, {
      user: user.name || "Anonymous",
      rating: newRating,
      comment: newComment
    });
    setSubmitting(false);
    setNewComment("");
    setNewRating(0);
    setMessage("Your review has been submitted and is pending approval.");
  };

  const averageRating =
    reviews.length > 0
      ? (reviews.reduce((acc, r) => acc + r.rating, 0) / reviews.length).toFixed(1)
      : "N/A";

  return (
    <section className="mt-12">
      <h2 className="text-2xl font-semibold text-navy-700 mb-4">Customer Reviews</h2>
      <div className="flex items-center mb-4">
        <StarRating rating={Number(averageRating)} />
        <p className="ml-2 text-gray-600 text-sm">
          Average Rating: {averageRating} ({reviews.length} reviews)
        </p>
      </div>

      {/* Review List */}
      {reviews.length === 0 ? (
        <p className="text-gray-600 mb-6">No reviews yet.</p>
      ) : (
        <div className="space-y-4 mb-10">
          {reviews.map((review) => (
            <div key={review.id} className="border border-gray-200 rounded p-4 shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <p className="font-semibold text-navy-700">{review.user}</p>
                <StarRating rating={review.rating} />
              </div>
              <p className="text-gray-700">{review.comment}</p>
            </div>
          ))}
        </div>
      )}

      {/* Review Form */}
      <form onSubmit={handleSubmit} className="bg-white shadow-md rounded p-4 space-y-3">
        <h3 className="text-lg font-semibold text-navy-700">Leave a Review</h3>
        <StarRating rating={newRating} onChange={setNewRating} editable />
        <textarea
          value={newComment}
          onChange={(e) => setNewComment(e.target.value)}
          placeholder="Write your review..."
          className="w-full border rounded p-2 focus:outline-none focus:border-navy-700"
          rows={3}
        />
        <button
          type="submit"
          disabled={submitting}
          className="btn-primary w-full sm:w-auto"
        >
          {submitting ? "Submitting..." : "Submit Review"}
        </button>
        {message && <p className="text-sm text-gray-600 mt-2">{message}</p>}
      </form>
    </section>
  );
};

export default ReviewSection;