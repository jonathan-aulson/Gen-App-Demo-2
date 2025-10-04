// Smooth scrolling, active navigation, and year update
const navLinks = document.querySelectorAll(".nav-link");
const sections = document.querySelectorAll("section");
const yearSpan = document.getElementById("year");

navLinks.forEach(link => {
  link.addEventListener("click", e => {
    e.preventDefault();
    const target = document.querySelector(link.getAttribute("href"));
    if (target) target.scrollIntoView({ behavior: "smooth" });
  });
});

window.addEventListener("scroll", () => {
  let current = "";
  sections.forEach(section => {
    const sectionTop = section.offsetTop - 100;
    if (scrollY >= sectionTop) current = section.getAttribute("id");
  });

  navLinks.forEach(link => {
    link.classList.remove("active");
    if (link.getAttribute("href") === `#${current}`) {
      link.classList.add("active");
    }
  });
});

yearSpan.textContent = new Date().getFullYear();

// Mobile menu toggle
const mobileMenu = document.getElementById("mobile-menu");
const navLinksContainer = document.querySelector(".nav-links");
if (mobileMenu && navLinksContainer) {
  mobileMenu.addEventListener("click", () => {
    navLinksContainer.classList.toggle("active");
  });
}

// Contact form validation and mock submission
const contactForm = document.getElementById("contact-form");
if (contactForm) {
  contactForm.addEventListener("submit", e => {
    e.preventDefault();
    const name = document.getElementById("name");
    const email = document.getElementById("email");
    const message = document.getElementById("message");
    const status = document.getElementById("form-status");

    if (!name.value || !email.value || !message.value) {
      status.textContent = "Please fill in all fields.";
      status.style.color = "red";
      return;
    }

    const emailPattern = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;
    if (!emailPattern.test(email.value)) {
      status.textContent = "Please enter a valid email address.";
      status.style.color = "red";
      return;
    }

    // Simulate successful submission
    status.textContent = "Sending...";
    status.style.color = "#007acc";

    setTimeout(() => {
      status.textContent = "Message sent successfully!";
      status.style.color = "green";
      contactForm.reset();
    }, 1000);
  });
}