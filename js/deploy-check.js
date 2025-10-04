// Deployment verification script for console testing
document.addEventListener("DOMContentLoaded", () => {
  console.log("Deployment check: Portfolio loaded successfully.");
  const contactForm = document.getElementById("contact-form");
  if (contactForm) {
    console.log("Contact form detected. Testing mock handler...");
    const testEvent = new Event("submit");
    contactForm.dispatchEvent(testEvent);
  } else {
    console.warn("Contact form not found. Verify index.html structure.");
  }
});