import React from "react";

interface StarRatingProps {
  rating: number;
  onChange?: (value: number) => void;
  editable?: boolean;
}

const StarRating: React.FC<StarRatingProps> = ({ rating, onChange, editable = false }) => {
  return (
    <div className="flex space-x-1 text-gold-500">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          className={`text-xl ${editable ? "cursor-pointer" : ""}`}
          onClick={() => editable && onChange && onChange(star)}
        >
          {star <= rating ? "★" : "☆"}
        </button>
      ))}
    </div>
  );
};

export default StarRating;