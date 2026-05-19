document.addEventListener("DOMContentLoaded", () => {
    document.addEventListener("submit", (e) => {
        const form = e.target;
        if (form.tagName !== "FORM" || form.hasAttribute("data-no-loader")) return;

        const submitButton = form.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.disabled = true;

            submitButton.innerHTML = `
                <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                <span class="visually-hidden">Loading...</span>
                Enviando...
            `;
        }
    });
});