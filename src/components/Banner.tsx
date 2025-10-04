import React from "react";
import { Link } from "react-router-dom";

const Banner: React.FC = () => {
  return (
    <section className="relative bg-navy-700 text-white py-16 px-6 md:px-12 rounded-lg overflow-hidden mb-12">
      <div className="absolute inset-0 bg-[url('/src/assets/banner-bg.jpg')] opacity-20 bg-cover bg-center"></div>
      <div className="relative z-10 text-center max-w-3xl mx-auto">
        <h1 className="text-4xl md:text-5xl font-bold mb-4">Welcome to BookHaven</h1>
        <p className="text-lg md:text-xl text-gray-200 mb-6">
          Discover your next favorite read from thousands of titles curated just for you.
        </p>
        <Link
          to="/catalog"
          className="inline-block bg-gold-500 text-white font-semibold py-3 px-6 rounded hover:bg-gold-700 transition"
        >
          Browse Catalog
        </Link>
      </div>
    </section>
  );
};

export default Banner;