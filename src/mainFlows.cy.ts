describe("BookHaven E2E Tests", () => {
  beforeEach(() => {
    cy.visit("/");
  });

  it("loads the homepage", () => {
    cy.contains("Welcome to BookHaven").should("be.visible");
  });

  it("navigates to catalog page", () => {
    cy.get("a").contains("Catalog").click();
    cy.url().should("include", "/catalog");
  });

  it("adds a book to cart and checks out", () => {
    cy.visit("/catalog");
    cy.get(".card").first().contains("View Details").click();
    cy.contains("Add to Cart").click();
    cy.visit("/cart");
    cy.contains("Proceed to Checkout").click();
    cy.url().should("include", "/checkout");
  });
});