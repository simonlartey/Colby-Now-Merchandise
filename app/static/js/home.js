document.addEventListener("DOMContentLoaded", function() {
  const urlParams = new URLSearchParams(window.location.search);

  // Auto-scroll to results when searching
  if (urlParams.get("search")) {
    const resultsSection = document.querySelector("#search-results");
    if (resultsSection) {
      resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  // Auto-reset search when cleared
  const input = document.getElementById("search-input");
  const form = document.getElementById("search-form");

  if (input && form) {
    input.addEventListener("input", function() {
      if (this.value === "") {
        window.location.href = form.getAttribute("action");
      }
    });
  }
});
