import { createSlice, PayloadAction } from "@reduxjs/toolkit";

interface Book {
  id: string;
  title: string;
  author: string;
  price: number;
  rating?: number;
  category?: string;
}

interface BooksState {
  list: Book[];
  loading: boolean;
  error: string | null;
}

const initialState: BooksState = {
  list: [],
  loading: false,
  error: null
};

const booksSlice = createSlice({
  name: "books",
  initialState,
  reducers: {
    setBooks: (state, action: PayloadAction<Book[]>) => {
      state.list = action.payload;
      state.loading = false;
      state.error = null;
    },
    startLoading: (state) => {
      state.loading = true;
    },
    setError: (state, action: PayloadAction<string>) => {
      state.loading = false;
      state.error = action.payload;
    }
  }
});

export const { setBooks, startLoading, setError } = booksSlice.actions;
export default booksSlice.reducer;