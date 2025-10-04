// Accessibility and SEO supportive scripts

document.addEventListener("DOMContentLoaded", () => {
  const yearSpan = document.getElementById("year");
  if (yearSpan) yearSpan.textContent = new Date().getFullYear();

  const navLinks = document.querySelectorAll(".nav-link");
  const sections = document.querySelectorAll("section");
  const menuToggle = document.getElementById("menu-toggle");
  const navList = document.querySelector("nav ul");
  const ctaBtn = document.getElementById("cta-btn");
  const contactForm = document.getElementById("contact-form");
  const filterButtons = document.querySelectorAll(".filter-btn");
  const projectCards = document.querySelectorAll(".project-card");

  // Keyboard navigation toggle support
  if (menuToggle) {
    menuToggle.addEventListener("keypress", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        navList.classList.toggle("show");
      }
    });
  }

  // Manage active link state
  window.addEventListener("scroll", () => {
    let current = "";
    sections.forEach((section) => {
      const sectionTop = section.offsetTop - 60;
      if (scrollY >= sectionTop) current = section.getAttribute("id");
    });
    navLinks.forEach((link) => {
      link.classList.remove("active");
      if (link.getAttribute("href") === `#${current}`) link.classList.add("active");
    });
  });

  // Smooth scrolling for CTA
  if (ctaBtn) {
    ctaBtn.addEventListener("click", () => {
      const projects = document.getElementById("projects");
      if (projects) projects.scrollIntoView({ behavior: "smooth" });
    });
  }

  // Contact Form Validation and Feedback
  if (contactForm) {
    contactForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const nameInput = document.getElementById("name");
      const emailInput = document.getElementById("email");
      const messageInput = document.getElementById("message");
      const formMessage = document.getElementById("form-message");

      let valid = true;
      formMessage.textContent = "";
      formMessage.className = "form-message";

      // Basic required validation
      [nameInput, emailInput, messageInput].forEach((input) => {
        if (!input.value.trim()) {
          input.classList.add("error");
          valid = false;
        } else {
          input.classList.remove("error");
        }
      });

      // Email format validation
      const emailPattern = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;
      if (emailInput.value && !emailPattern.test(emailInput.value)) {
        emailInput.classList.add("error");
        valid = false;
        formMessage.textContent = "Please enter a valid email address.";
        formMessage.classList.add("error");
      }

      if (valid) {
        formMessage.textContent = "Message sent successfully!";
        formMessage.classList.add("success");
        contactForm.reset();
      } else if (!formMessage.textContent) {
        formMessage.textContent = "Please fill out all required fields.";
        formMessage.classList.add("error");
      }
    });
  }

  // Project Filtering (simple demo)
  if (filterButtons.length > 0 && projectCards.length > 0) {
    filterButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        const category = btn.dataset.category;
        filterButtons.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        projectCards.forEach((card) => {
          if (category === "all" || card.dataset.category === category) {
            card.style.display = "block";
          } else {
            card.style.display = "none";
          }
        });
      });
    });
  }
});