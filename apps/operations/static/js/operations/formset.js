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

        let html = template.innerHTML.replace(/__prefix__/g, formCount)
            .replace(/id="([^"]*)"/g, (match, id) => `id="${id.replace(/__prefix__/g, formCount)}"`);

        container.insertAdjacentHTML('beforeend', html);
        totalForms.value = formCount + 1;

        const lastRow = container.lastElementChild;
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
        if (select) this.initSelect2(select, index);
    },

    initSelect2: function (select, index) {
        $(select).select2({
            theme: 'bootstrap-5',
            width: '100%',
            ajax: {
                url: supplySearchUrl,
                dataType: 'json',
                delay: 300,
                data: (params) => ({q: params.term, type: 1}),
                processResults: (data) => ({
                    results: data.results.map(i => ({...i, id: i.id, text: i.text}))
                })
            }
        }).on('select2:select', (e) => this.handleSelection(select, e.params.data));
    },

    handleSelection: function (selectElement, data) {
        const row = selectElement.closest('.form-row');
        const stock = parseFloat(data.stock || 0);

        row.querySelector('.current-stock').textContent = stock;
        const newStockSpan = row.querySelector('.new-stock');
        const qtyInput = row.querySelector('input[name$="-quantity_requested"]');

        qtyInput.oninput = null;
        qtyInput.addEventListener('input', function () {
            let val = Math.min(parseFloat(this.value) || 0, stock);
            if (this.value != val) this.value = val;

            const remaining = stock - val;
            newStockSpan.textContent = remaining;
            newStockSpan.style.color = remaining === 0 ? 'green' : 'orange';
        }, {once: false});
    },

    hydrateRows: async function () {
        const rows = document.querySelectorAll('.form-row:not([style*="display: none"])');
        for (const row of rows) {
            const select = row.querySelector('select[name$="-supply"]');
            if (select && select.value) {
                const codeToSearch = select.value; // Este es el código (ej: 'DES-8153')
                try {
                    // Usamos el mismo parámetro 'q' que usa tu buscador AJAX
                    const response = await fetch(`${supplySearchUrl}?q=${encodeURIComponent(codeToSearch)}&type=1`);
                    const data = await response.json();

                    const match = data.results.find(i => i.code === codeToSearch || i.id == codeToSearch);

                    if (match) {
                        this.handleSelection(select, match);

                        const qtyInput = row.querySelector('input[name$="-quantity_requested"]');
                        if (qtyInput && qtyInput.value > 0) {
                            qtyInput.dispatchEvent(new Event('input'));
                        }
                    }
                } catch (error) {
                    console.error("Error al hidratar la fila:", error);
                }
            }
        }
    }
};


document.addEventListener("DOMContentLoaded", function () {
    const container = document.getElementById('form-container');
    const totalForms = document.querySelector("input[name$='-TOTAL_FORMS']");

    if (container && totalForms) {
        FormsetManager.init(container, totalForms, InventoryLogic.initRow.bind(InventoryLogic));

        container.querySelectorAll('.form-row').forEach((row, idx) => InventoryLogic.initRow(row, idx));

        InventoryLogic.hydrateRows();
    }
});
