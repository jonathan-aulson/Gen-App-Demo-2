export interface Book {
  id: string;
  title: string;
  author: string;
  price: number;
  coverImage: string;
}

export async function fetchFeaturedBooks(): Promise<Book[]> {
  // Simulating API call with mock data
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve([
        {
          id: "1",
          title: "The Great Gatsby",
          author: "F. Scott Fitzgerald",
          price: 12.99,
          coverImage: "https://placehold.co/200x300?text=Gatsby"
        },
        {
          id: "2",
          title: "To Kill a Mockingbird",
          author: "Harper Lee",
          price: 10.99,
          coverImage: "https://placehold.co/200x300?text=Mockingbird"
        },
        {
          id: "3",
          title: "1984",
          author: "George Orwell",
          price: 9.99,
          coverImage: "https://placehold.co/200x300?text=1984"
        },
        {
          id: "4",
          title: "Pride and Prejudice",
          author: "Jane Austen",
          price: 11.49,
          coverImage: "https://placehold.co/200x300?text=Pride+%26+Prejudice"
        }
      ]);
    }, 500);
  });
}