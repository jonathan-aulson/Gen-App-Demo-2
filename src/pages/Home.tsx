import React, { useEffect, useState } from "react";
import LazyImage from "../components/LazyImage";
import { fetchFeaturedBooks, Book } from "../services/bookService";
import { Link } from "react-router-dom";

const Home: React.FC = () => {
  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadBooks = async () => {
      const data = await fetchFeaturedBooks();
      setBooks(data);
      setLoading(false);
    };
    loadBooks();
  }, []);

  return (
    <div className="container mx-auto px-4 py-8">
      <section className="text-center mb-12">
        <h1 className="text-4xl font-bold text-navy-700 mb-4">Welcome to BookHaven</h1>
        <p className="text-gray-600 max-w-2xl mx-auto">
          Discover books you'll love. Browse through thousands of titles with personalized
          recommendations and secure checkout.
        </p>
      </section>

      <section>
        <h2 className="text-2xl font-semibold text-navy-700 mb-6">Featured Books</h2>
        {loading ? (
          <p className="text-gray-600 text-center">Loading featured books...</p>
        ) : (
          <div className="grid-responsive">
            {books.map((book) => (
              <div key={book.id} className="card">
                <LazyImage
                  src={book.coverImage}
                  alt={book.title}
                  className="rounded-md w-full h-64 object-cover mb-3"
                />
                <h3 className="text-lg font-semibold text-navy-700 truncate">{book.title}</h3>
                <p className="text-sm text-gray-600 truncate">{book.author}</p>
                <p className="text-gold-500 font-medium mt-2">${book.price}</p>
                <Link to={`/book/${book.id}`} className="btn-secondary mt-3 inline-block text-sm">
                  View Details
                </Link>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
};

export default Home;