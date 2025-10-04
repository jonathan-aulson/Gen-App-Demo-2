import React, { useState } from "react";

interface ContactForm {
  name: string;
  email: string;
  message: string;
}

const Contact: React.FC = () => {
  const [form, setForm] = useState<ContactForm>({ name: "", email: "", message: "" });
  const [submitting, setSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setSuccessMessage("");
    setErrorMessage("");

    try {
      // Simulate backend API call
      await new Promise((resolve) => setTimeout(resolve, 1000));
      setSubmitting(false);
      setSuccessMessage("Thank you for contacting us! We'll get back to you soon.");
      setForm({ name: "", email: "", message: "" });
    } catch (error) {
      setSubmitting(false);
      setErrorMessage("Something went wrong. Please try again later.");
    }
  };

  return (
    <div className="container mx-auto px-4 py-12 max-w-2xl">
      <h1 className="text-4xl font-bold text-navy-700 mb-6 text-center">Contact Us</h1>
      <p className="text-gray-700 mb-8 text-center">
        Have a question, suggestion, or need support? Fill out the form below and our team will get
        back to you shortly.
      </p>
      <form
        onSubmit={handleSubmit}
        className="bg-white shadow-md rounded-lg p-6 space-y-4"
      >
        {successMessage && (
          <p className="text-green-600 text-sm text-center">{successMessage}</p>
        )}
        {errorMessage && (
          <p className="text-red-600 text-sm text-center">{errorMessage}</p>
        )}
        <div>
          <label className="block text-gray-700 font-medium mb-1">Full Name</label>
          <input
            type="text"
            name="name"
            required
            value={form.name}
            onChange={handleChange}
            className="w-full border rounded p-2 focus:outline-none focus:border-navy-700"
            placeholder="Your name"
          />
        </div>
        <div>
          <label className="block text-gray-700 font-medium mb-1">Email</label>
          <input
            type="email"
            name="email"
            required
            value={form.email}
            onChange={handleChange}
            className="w-full border rounded p-2 focus:outline-none focus:border-navy-700"
            placeholder="you@example.com"
          />
        </div>
        <div>
          <label className="block text-gray-700 font-medium mb-1">Message</label>
          <textarea
            name="message"
            required
            value={form.message}
            onChange={handleChange}
            className="w-full border rounded p-2 focus:outline-none focus:border-navy-700"
            rows={5}
            placeholder="Write your message here..."
          ></textarea>
        </div>
        <button
          type="submit"
          disabled={submitting}
          className="btn-primary w-full sm:w-auto"
        >
          {submitting ? "Sending..." : "Send Message"}
        </button>
      </form>
      <div className="text-center mt-8 text-gray-700">
        <p>Email: <a href="mailto:support@bookhaven.com" className="text-navy-700 hover:text-gold-500">support@bookhaven.com</a></p>
        <p>Phone: <a href="tel:+1234567890" className="text-navy-700 hover:text-gold-500">+1 (234) 567-890</a></p>
        <p>Address: 123 Reading Lane, Storyville, USA</p>
      </div>
    </div>
  );
};

export default Contact;