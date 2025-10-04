import React from "react";
import { Link, NavLink } from "react-router-dom";

const Navbar: React.FC = () => {
  const navLinks = [
    { to: "/", label: "Home" },
    { to: "/catalog", label: "Catalog" },
    { to: "/cart", label: "Cart" },
    { to: "/account", label: "Account" },
    { to: "/about", label: "About" },
    { to: "/contact", label: "Contact" }
  ];

  return (
    <nav className="sticky top-0 z-50 bg-white shadow-md border-b border-gray-100">
      <div className="container mx-auto flex items-center justify-between px-4 py-3">
        <Link
          to="/"
          className="text-2xl font-bold text-navy-700 tracking-wide hover:text-gold-500 transition"
        >
          📚 BookHaven
        </Link>
        <div className="hidden md:flex space-x-6">
          {navLinks.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                `hover:text-gold-500 transition ${
                  isActive ? "text-gold-500 font-semibold" : "text-gray-700"
                }`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </div>
        <div className="md:hidden">
          <button
            aria-label="Menu"
            className="p-2 rounded bg-navy-700 text-white hover:bg-navy-500"
          >
            ☰
          </button>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;