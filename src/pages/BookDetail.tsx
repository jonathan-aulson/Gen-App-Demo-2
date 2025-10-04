import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useAppDispatch } from "../store/hooks";
import { addToCart } from "../store/slices/cartSlice";
import { fetchFeaturedBooks, Book } from "../services/bookService";
import ReviewSection from "../components/ReviewSection";

const BookDetail: React.FC = () => {
  const { id } = useParams();
  const [book, setBook] = useState<Book | null>(null);
  const [related, setRelated] = useState<Book[]>([]);
  const [wishlist, setWishlist] = useState<Book[]>([]);
  const dispatch = useAppDispatch();

  const loadBook = async () => {
    const allBooks = await fetchFeaturedBooks();
    const current = allBooks.find(b => b.id === id) || null;
    setBook(current);
    if (current) {
      const recs = allBooks.filter(b => b.category === current.category && b.id !== current.id);
      setRelated(recs);
    }
  };

  const handleAddToCart = () => {
    if (book) dispatch(addToCart(book));
  };

  const handleAddToWishlist = () => {
    if (book && !wishlist.find(b => b.id === book.id)) {
      setWishlist([...wishlist, book]);
    }
  };

  const handleImageError = (e: React.SyntheticEvent<HTMLImageElement>) => {
    e.currentTarget.src = "/placeholder-book.png";
  };

  useEffect(() => {
    loadBook();
  }, [id]);

  if (!book) return <p>Loading book...</p>;

  return (
    <div className="p-6">
      <div className="flex gap-6">
        <img
          src={book.coverImage}
          alt={book.title}
          onError={handleImageError}
          className="w-48 h-64 object-cover"
        />
        <div>
          <h1 className="text-2xl font-bold">{book.title}</h1>
          <p className="text-gray-700">{book.author}</p>
          <p className="text-lg font-semibold">${book.price}</p>
          <button onClick={handleAddToCart} className="bg-green-600 text-white p-2 rounded mr-2">
            Add to Cart
          </button>
          <button onClick={handleAddToWishlist} className="bg-blue-500 text-white p-2 rounded">
            Add to Wishlist
          </button>
        </div>
      </div>

      <div className="mt-6">
        <h2 className="text-xl font-semibold mb-2">Related Books</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {related.map(r => (
            <div key={r.id} className="border p-2 rounded">
              <img src={r.coverImage} alt={r.title} onError={handleImageError} className="w-full h-40 object-cover" />
              <p>{r.title}</p>
            </div>
          ))}
          {related.length === 0 && <p>No related books found.</p>}
        </div>
      </div>

      <ReviewSection bookId={id || ""} />
    </div>
  );
};

export default BookDetail;