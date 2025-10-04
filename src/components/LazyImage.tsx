import React, { useState, useEffect } from "react";

interface LazyImageProps {
  src: string;
  alt: string;
  className?: string;
  placeholder?: string;
}

const LazyImage: React.FC<LazyImageProps> = ({
  src,
  alt,
  className = "",
  placeholder = "https://placehold.co/200x300?text=Loading..."
}) => {
  const [imageSrc, setImageSrc] = useState(placeholder);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    const img = new Image();
    img.src = src;
    img.onload = () => {
      setImageSrc(src);
      setLoaded(true);
    };
  }, [src]);

  return (
    <img
      src={imageSrc}
      alt={alt}
      className={`${className} transition-opacity duration-500 ${
        loaded ? "opacity-100" : "opacity-60"
      }`}
      loading="lazy"
    />
  );
};

export default LazyImage;