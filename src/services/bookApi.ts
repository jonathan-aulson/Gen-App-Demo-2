import api from "./api";

export interface Book {
  id: string;
  title: string;
  author: string;
  price: number;
  description?: string;
  coverImage?: string;
  rating?: number;
  category?: string;
}

export async function getBooks(): Promise<Book[]> {
  try {
    const response = await api.get("/books");
    return response.data;
  } catch (error) {
    console.error("Failed to fetch books:", error);
    throw error;
  }
}

export async function getBookById(id: string): Promise<Book> {
  try {
    const response = await api.get(`/books/${id}`);
    return response.data;
  } catch (error) {
    console.error("Failed to fetch book:", error);
    throw error;
  }
}

export async function createBook(book: Book): Promise<Book> {
  try {
    const response = await api.post("/books", book);
    return response.data;
  } catch (error) {
    console.error("Failed to create book:", error);
    throw error;
  }
}

export async function updateBook(id: string, book: Book): Promise<Book> {
  try {
    const response = await api.put(`/books/${id}`, book);
    return response.data;
  } catch (error) {
    console.error("Failed to update book:", error);
    throw error;
  }
}

export async function deleteBook(id: string): Promise<void> {
  try {
    await api.delete(`/books/${id}`);
  } catch (error) {
    console.error("Failed to delete book:", error);
    throw error;
  }
}