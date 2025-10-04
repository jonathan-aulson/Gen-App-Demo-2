import cartReducer, { addToCart, removeFromCart, clearCart } from "../slices/cartSlice";

describe("cartSlice", () => {
  const initialState = { items: [] };

  test("should return initial state", () => {
    expect(cartReducer(undefined, { type: undefined })).toEqual(initialState);
  });

  test("should handle addToCart", () => {
    const newItem = { id: "1", title: "Book One", price: 10, quantity: 1 };
    const nextState = cartReducer(initialState, addToCart(newItem));
    expect(nextState.items.length).toBe(1);
    expect(nextState.items[0].title).toBe("Book One");
  });

  test("should handle removeFromCart", () => {
    const state = { items: [{ id: "1", title: "Book One", price: 10, quantity: 1 }] };
    const nextState = cartReducer(state, removeFromCart("1"));
    expect(nextState.items.length).toBe(0);
  });

  test("should handle clearCart", () => {
    const state = { items: [{ id: "1", title: "Book One", price: 10, quantity: 1 }] };
    const nextState = cartReducer(state, clearCart());
    expect(nextState.items).toEqual([]);
  });
});