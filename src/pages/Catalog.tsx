import React, { useEffect, useState } from "react";
import { fetchFeaturedBooks, Book } from "../services/bookService";

const Catalog: React.FC = () => {
  const [books, setBooks] = useState<Book[]>([]);
  const [search, setSearch] = useState("");
  const [author, setAuthor] = useState("");
  const [genre, setGenre] = useState("");
  const [sort, setSort] = useState("");
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const itemsPerPage = 8;

  const loadBooks = async () => {
    setLoading(true);
    try {
      const allBooks = await fetchFeaturedBooks();
      let filtered = [...allBooks];

      if (search.trim()) {
        filtered = filtered.filter(b =>
          b.title.toLowerCase().includes(search.toLowerCase())
        );
      }
      if (author.trim()) {
        filtered = filtered.filter(b =>
          b.author.toLowerCase().includes(author.toLowerCase())
        );
      }
      if (genre.trim()) {
        filtered = filtered.filter(b => b.category === genre);
      }

      if (sort === "priceAsc") {
        filtered.sort((a, b) => a.price - b.price);
      } else if (sort === "priceDesc") {
        filtered.sort((a, b) => b.price - a.price);
      } else if (sort === "releaseDate") {
        filtered.sort(
          (a, b) =>
            new Date(b.releaseDate).getTime() - new Date(a.releaseDate).getTime()
        );
      }

      const startIndex = (page - 1) * itemsPerPage;
      const paginated = filtered.slice(startIndex, startIndex + itemsPerPage);

      if (paginated.length === 0) {
        setError("No results found");
      } else {
        setError("");
      }

      setBooks(paginated);
    } catch (e) {
      setError("Failed to load books");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBooks();
  }, [search, author, genre, sort, page]);

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold mb-4">Catalog</h1>
      <div className="flex flex-wrap gap-2 mb-4">
        <input
          type="text"
          placeholder="Search by title..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="border p-2 rounded"
        />
        <input
          type="text"
          placeholder="Filter by author..."
          value={author}
          onChange={e => setAuthor(e.target.value)}
          className="border p-2 rounded"
        />
        <select
          value={genre}
          onChange={e => setGenre(e.target.value)}
          className="border p-2 rounded"
        >
          <option value="">All Genres</option>
          <option value="Fiction">Fiction</option>
          <option value="Non-fiction">Non-fiction</option>
          <option value="Academic">Academic</option>
        </select>
        <select
          value={sort}
          onChange={e => setSort(e.target.value)}
          className="border p-2 rounded"
        >
          <option value="">Sort By</option>
          <option value="priceAsc">Price: Low to High</option>
          <option value="priceDesc">Price: High to Low</option>
          <option value="releaseDate">Release Date</option>
        </select>
      </div>

      {loading && <p>Loading...</p>}
      {!loading && error && <p className="text-red-600">{error}</p>}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {books.map(book => (
          <div key={book.id} className="border p-2 rounded shadow-sm">
            <img
              src={book.coverImage}
              alt={book.title}
              className="w-full h-40 object-cover"
            />
            <h2 className="font-bold">{book.title}</h2>
            <p>{book.author}</p>
            <p>${book.price}</p>
          </div>
        ))}
      </div>

      <div className="flex justify-center gap-4 mt-4">
        <button
          disabled={page === 1}
          onClick={() => setPage(page - 1)}
          className="bg-gray-200 p-2 rounded"
        >
          Prev
        </button>
        <span>Page {page}</span>
        <button
          onClick={() => setPage(page + 1)}
          className="bg-gray-200 p-2 rounded"
        >
          Next
        </button>
      </div>
    </div>
  );
};

export default Catalog;