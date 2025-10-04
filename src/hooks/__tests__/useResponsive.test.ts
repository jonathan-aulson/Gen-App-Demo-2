import { renderHook, act } from "@testing-library/react";
import { useResponsive } from "../useResponsive";

describe("useResponsive Hook", () => {
  test("detects mobile view", () => {
    global.innerWidth = 500;
    const { result } = renderHook(() => useResponsive());
    expect(result.current.isMobile).toBe(true);
  });

  test("detects desktop view", () => {
    global.innerWidth = 1200;
    const { result } = renderHook(() => useResponsive());
    act(() => {
      global.dispatchEvent(new Event("resize"));
    });
    expect(result.current.isMobile).toBe(false);
  });
});