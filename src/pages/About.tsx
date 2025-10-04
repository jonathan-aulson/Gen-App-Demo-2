import React from "react";

const About: React.FC = () => {
  return (
    <div className="container mx-auto px-4 py-12 max-w-3xl">
      <h1 className="text-4xl font-bold text-navy-700 mb-6 text-center">About BookHaven</h1>
      <p className="text-gray-700 leading-relaxed mb-6">
        Welcome to <span className="font-semibold text-navy-700">BookHaven</span> — your ultimate
        online destination for discovering, exploring, and purchasing books. Our mission is to
        connect readers with stories that inspire, educate, and entertain. From best-selling novels
        to academic resources, BookHaven offers a curated selection designed to meet the diverse
        interests of book lovers around the world.
      </p>
      <p className="text-gray-700 leading-relaxed mb-6">
        Established in 2024, BookHaven was founded with the vision of making literature accessible
        to everyone, everywhere. We believe books have the power to transform lives, spark
        creativity, and foster understanding across cultures. Our platform combines modern
        technology with a love for reading to create a seamless and personalized shopping
        experience.
      </p>
      <p className="text-gray-700 leading-relaxed">
        Whether you're a casual reader or a lifelong bibliophile, our goal is to make your reading
        journey enjoyable, affordable, and inspiring. Thank you for being part of the BookHaven
        community!
      </p>
    </div>
  );
};

export default About;