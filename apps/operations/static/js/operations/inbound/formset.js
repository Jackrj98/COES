const FormsetManager = {
    init: function (container, totalForms, onRowAdded) {
        document.getElementById('add-form')?.addEventListener('click', () => this.addRow(container, totalForms, onRowAdded));
        container.addEventListener('click', (e) => {
            if (e.target.closest('.remove-row')) this.removeRow(e.target.closest('.remove-row'), container, totalForms);
        });
    },

    addRow: function (container, totalForms, onRowAdded) {
        const formCount = parseInt(totalForms.value);
        const template = document.getElementById('empty-form-template');
        if (!template) return;

        // Limpiar template: reemplazar __prefix__ y corregir IDs/Names
        let html = template.innerHTML.replace(/__prefix__/g, formCount)
            .replace(/id="([^"]*)"/g, (match, id) => `id="${id.replace(/__prefix__/g, formCount)}"`);

        container.insertAdjacentHTML('beforeend', html);
        totalForms.value = formCount + 1;

        const lastRow = container.lastElementChild;
        // IMPORTANTE: Llamar al callback para inicializar Select2 en la nueva fila
        if (onRowAdded) onRowAdded(lastRow, formCount);
    },

    removeRow: function (deleteButton, container, totalForms) {
        const row = deleteButton.closest('.form-row');
        const deleteCheckbox = row.querySelector('input[type="checkbox"][name$="-DELETE"]');
        if (deleteCheckbox) {
            deleteCheckbox.checked = true;
            row.style.display = 'none';
        } else {
            row.remove();
            totalForms.value = parseInt(totalForms.value) - 1;
            this.renumber(container);
        }
    },

    renumber: function (container) {
        const rows = container.querySelectorAll('.form-row:not([style*="display: none"])');
        rows.forEach((row, index) => {
            row.querySelectorAll('[name*="-"], [id*="-"]').forEach(el => {
                el.name = el.name.replace(/-\d+-/, `-${index}-`);
                el.id = el.id.replace(/-\d+-/, `-${index}-`);
            });
        });
    }
};

const InventoryLogic = {
    initRow: function (row, index) {
        const select = row.querySelector('select[name$="-supply"]');
        if (select) this.initSelect2(select);
    },

    initSelect2: function (select) {
        if ($(select).hasClass("select2-hidden-accessible")) return;

        $(select).select2({
            theme: 'bootstrap-5',
            width: '100%',
            placeholder: "Seleccione un insumo",
            allowClear: true
        });
    }
};

document.addEventListener("DOMContentLoaded", function () {
    const container = document.getElementById('form-container');
    const totalForms = document.querySelector("input[name$='-TOTAL_FORMS']");

    if (container && totalForms) {
        FormsetManager.init(container, totalForms, (row, idx) => {
            InventoryLogic.initRow(row, idx);
        });

        container.querySelectorAll('.form-row').forEach((row, idx) => {
            InventoryLogic.initRow(row, idx);
        });
    }
});