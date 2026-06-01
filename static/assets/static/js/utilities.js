document.addEventListener("DOMContentLoaded", () => {
    $('.select2').each(function() {
        $(this).select2({
            theme: "bootstrap-5",
            width: '100%',
            dropdownParent: $(this).parent(),
        });
    });
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

    let tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    let tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl, {
            delay: {show: 200, hide: 100},
            trigger: 'hover'
        });
    });
});

function getCookie(name) {
    let value = "; " + document.cookie;
    let parts = value.split("; " + name + "=");
    if (parts.length == 2) return parts.pop().split(";").shift();
}


function parseDateTime(data) {
    const date = new Date(data);
    if (!data || isNaN(date.getTime())) return {date: "---", time: "---", full: "---"};

    const day = date.getDate();
    const month = date.toLocaleString('es-ES', {month: 'short'});
    const year = date.getFullYear();
    const time = date.toLocaleTimeString('es-ES', {hour: '2-digit', minute: '2-digit', hour12: false});

    const getOrdinal = (n) => {
        const s = ["th", "st", "nd", "rd"];
        const v = n % 100;
        return s[(v - 20) % 10] || s[v] || s[0];
    };

    return {
        date: `${day} ${month.charAt(0).toUpperCase() + month.slice(1)} ${year}`,
        time: time,
        full: `${month.charAt(0).toUpperCase() + month.slice(1)} ${day}${getOrdinal(day)} ${year}`,
        raw: date
    };
}

const capitalize = (str) =>
    str.toLowerCase().replace(/\b\w/g, (char) => char.toUpperCase());
