import { configureStore, combineReducers } from "@reduxjs/toolkit";
import { persistReducer, persistStore } from "redux-persist";
import storage from "redux-persist/lib/storage";
import userReducer from "./slices/userSlice";
import cartReducer from "./slices/cartSlice";
import booksReducer from "./slices/booksSlice";

const rootReducer = combineReducers({
  user: userReducer,
  cart: cartReducer,
  books: booksReducer
});

const persistConfig = {
  key: "bookhaven-root",
  storage,
  whitelist: ["user", "cart"]
};

const persistedReducer = persistReducer(persistConfig, rootReducer);

export const store = configureStore({
  reducer: persistedReducer,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: false
    })
});

export const persistor = persistStore(store);

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;