document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("global-search-input");
    const box = document.getElementById("search-suggestions");
    const form = document.getElementById("global-search-form");

    if (!input || !box || !form) return;  // Safety check

    let timeout = null;

    input.addEventListener("input", () => {
        const query = input.value.trim();
        clearTimeout(timeout);

        if (query.length === 0) {
            box.style.display = "none";
            return;
        }

        // Add slight delay to improve performance
        timeout = setTimeout(() => {
            fetch(`/autocomplete?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(items => {
                    if (!items || items.length === 0) {
                        box.style.display = "none";
                        return;
                    }

                    box.innerHTML = items.map(item => `
                        <a href="/item/${item.id}" 
                           class="d-flex align-items-center p-2 text-decoration-none text-dark"
                           style="border-bottom: 1px solid #f1f1f1;">
                            <img src="${item.image}" 
                                 style="width: 40px; height: 40px; object-fit: cover; border-radius: 6px; margin-right: 10px;">
                            <span>${item.title}</span>
                        </a>
                    `).join("");

                    box.style.display = "block";
                })
                .catch(() => {
                    box.style.display = "none";
                });
        }, 200);
    });

    // Hide box when clicking outside
    document.addEventListener("click", (event) => {
        if (!form.contains(event.target)) {
            box.style.display = "none";
        }
    });

    // Hide suggestions on form submit
    form.addEventListener("submit", () => {
        box.style.display = "none";
    });
});
