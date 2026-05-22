// FAQ accordion
document.querySelectorAll(".faq-q").forEach(btn => {
  btn.addEventListener("click", () => {
    const answer = btn.nextElementSibling;
    const isOpen = btn.classList.contains("open");
    document.querySelectorAll(".faq-q").forEach(b => {
      b.classList.remove("open");
      b.nextElementSibling.classList.remove("open");
    });
    if (!isOpen) {
      btn.classList.add("open");
      answer.classList.add("open");
    }
  });
});

// Stripe buy button
document.querySelectorAll(".buy-btn[data-checkout]").forEach(btn => {
  btn.addEventListener("click", async e => {
    e.preventDefault();
    const original = btn.textContent;
    btn.textContent = "Loading…";
    btn.style.opacity = ".7";

    try {
      const res = await fetch("/api/stripe/checkout", { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Could not start checkout.");
      window.location.href = data.url;
    } catch (err) {
      alert("Could not start checkout: " + err.message);
      btn.textContent = original;
      btn.style.opacity = "1";
    }
  });
});
