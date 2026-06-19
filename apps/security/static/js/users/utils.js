document.addEventListener("DOMContentLoaded", () => {
    function setupPasswordToggle(toggleId, inputId) {
        const toggle = document.querySelector(toggleId);
        const input = document.querySelector(inputId);

        if (toggle && input) {
            toggle.addEventListener('click', () => {
                const isPassword = input.type === 'password';
                input.type = isPassword ? 'text' : 'password';

                const icon = toggle.querySelector('i');
                if (icon) {
                    icon.classList.toggle('bi-eye', !isPassword);
                    icon.classList.toggle('bi-eye-slash', isPassword);
                }
            });
        }
    }

    document.querySelectorAll('[data-target]').forEach(btn => {
        if (btn.classList.contains('toggle-password') || btn.id === 'toggle-password') {
            btn.addEventListener('click', function() {
                const input = document.getElementById(this.dataset.target);
                if (!input) return;

                const isPassword = input.type === 'password';
                input.type = isPassword ? 'text' : 'password';

                const icon = this.querySelector('i');
                if (icon) {
                    icon.classList.toggle('bi-eye', !isPassword);
                    icon.classList.toggle('bi-eye-slash', isPassword);
                }
            });
        }
    });

    setupPasswordToggle('#toggle-current-password', '#id_current_password');
    setupPasswordToggle('#toggle-new-password', '#id_new_password');
    setupPasswordToggle('#toggle-confirm-password', '#id_confirm_password');

    const genericToggle = document.querySelector('#toggle-password');
    const genericPassword = document.querySelector('#id_password');
    if (genericToggle && genericPassword && !genericToggle.hasAttribute('data-target')) {
        setupPasswordToggle('#toggle-password', '#id_password');
    }
});