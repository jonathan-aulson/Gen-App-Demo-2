import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import Navbar from "../Navbar";

describe("Navbar Component", () => {
  test("renders BookHaven logo", () => {
    render(
      <BrowserRouter>
        <Navbar />
      </BrowserRouter>
    );
    const logo = screen.getByText(/BookHaven/i);
    expect(logo).toBeInTheDocument();
  });

  test("contains navigation links", () => {
    render(
      <BrowserRouter>
        <Navbar />
      </BrowserRouter>
    );
    const links = screen.getAllByRole("link");
    expect(links.length).toBeGreaterThan(0);
  });
});