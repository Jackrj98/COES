document.addEventListener("DOMContentLoaded", function () {
    const container = document.getElementById('form-container');
    const totalForms = document.querySelector("input[name$='-TOTAL_FORMS']");

    if (!container || !totalForms) {
        console.error("Formset elements not found!");
        return;
    }

    initializeFormset(container, totalForms);
});

function initializeFormset(container, totalForms) {
    initializeAddButton(container, totalForms);
    initializeRemoveHandler(container, totalForms);

    initializeExistingSelect2(container);
}

function initializeExistingSelect2(container) {
    const existingSelects = container.querySelectorAll('select[name$="-supply"]');
    existingSelects.forEach((select, index) => {
        initializeSelect2WithAjax(select, index);
    });
}

function initializeSelect2WithAjax(selectElement, formIndex) {
    if (typeof $ === 'undefined' || !$.fn.select2) {
        console.error('Select2 no está cargado');
        return;
    }

    if ($(selectElement).data('select2')) {
        $(selectElement).select2('destroy');
    }

    $(selectElement).closest('.form-row').find('.select2-container').remove();

    if (!selectElement.id && formIndex !== undefined) {
        selectElement.id = `id_movement_set-${formIndex}-supply`;
    }

    $(selectElement).select2({
        theme: 'bootstrap-5',
        width: '100%',
        placeholder: 'Buscar por nombre o código...',
        allowClear: true,
        language: {
            searching: function () {
                return "Buscando...";
            },
            noResults: function () {
                return "No se encontraron insumos";
            },
            inputTooShort: function () {
                return "Escribe al menos 1 carácter";
            }
        },
        ajax: {
            url: supplySearchUrl,
            dataType: 'json',
            delay: 300,
            data: function (params) {
                const selectedIds = Array.from(document.querySelectorAll('select[name$="-supply"]'))
                    .map(s => s.value)
                    .filter(id => id && id !== selectElement.value);
                return {
                    q: params.term,
                    exclude_ids: selectedIds.join(',')
                };
            },
            processResults: function (data) {
                return {
                    results: data.results.map(item => ({
                        id: item.code,
                        text: item.text,
                        code: item.code,
                        name: item.name,
                        stock: item.stock
                    }))
                };
            },
            cache: false
        },
        minimumInputLength: 1,
        templateResult: formatSupplyResult,
        templateSelection: formatSupplySelection
    });

    $(selectElement).on('select2:select', function (e) {
        const selectedData = e.params.data;
        handleSupplySelection(selectElement, selectedData);
    });

    $(selectElement).on('select2:clear', function () {
        clearSupplySelection(selectElement);
    });
}

function formatSupplyResult(supply) {
    if (supply.loading) {
        return supply.text;
    }

    if (!supply.code) {
        return supply.text;
    }
    return $(`
        <div class="d-flex justify-content-between align-items-center w-100">
            <div>
                <strong>${escapeHtml(supply.text)}</strong><br>
                <small class="text-muted">${escapeHtml(supply.code)}</small>
            </div>
            <div class="badge bg-secondary ms-2">
                Stock: ${supply.stock || 0}
            </div>
        </div>
    `);
}

function formatSupplySelection(supply) {
    if (!supply.code) {
        return supply.text || '';
    }
    return `${supply.text} - ${supply.code}`;
}

const operations = {
    0: (stock, qty) => stock + qty, // Entrada: Suma
    1: (stock, qty) => stock - qty, // Salida: Resta
    2: (stock, qty) => qty          // Ajuste: El valor es el nuevo stock
};

function handleSupplySelection(selectElement, supplyData) {
    const row = selectElement.closest('.form-row');
    if (!row) return;

    const typeInput = document.getElementById("id_movement_type");
    const movementIndex = typeInput ? parseInt(typeInput.value) : null;

    selectElement.value = supplyData.code;
    const currentStockSpan = row.querySelector('.current-stock');
    const newStockSpan = row.querySelector('.new-stock');
    const quantityInput = row.querySelector('input[name$="-quantity"]');

    if (supplyData.stock !== undefined) {
        const stock = parseFloat(supplyData.stock);

        if (currentStockSpan) currentStockSpan.textContent = stock;
        if (newStockSpan) newStockSpan.textContent = stock;

        if (quantityInput) {
            const isOutbound = movementIndex === 1;
            if (isOutbound) {
                quantityInput.max = stock;
                quantityInput.placeholder = `Máx: ${stock}`;
            } else {
                quantityInput.removeAttribute('max');
                quantityInput.placeholder = '';
            }

            quantityInput.oninput = function () {
                let qty = parseFloat(this.value) || 0;
                if (isOutbound && qty > stock) {
                    qty = stock;
                    this.value = stock;
                }


                const calculate = operations[movementIndex] || ((s) => s);
                const nuevoStock = calculate(stock, qty);
                if (newStockSpan) {
                    newStockSpan.textContent = nuevoStock;

                    newStockSpan.style.color = (nuevoStock < 0) ? 'red' : 'orange';
                }
            };
        }
    }

    selectElement.setAttribute('data-supply-code', supplyData.code);
    selectElement.setAttribute('data-supply-stock', supplyData.stock);

    const event = new CustomEvent('supplySelected', {
        detail: {supply: supplyData, row: row, type: movementIndex}
    });
    row.dispatchEvent(event);
}

function clearSupplySelection(selectElement) {
    const row = selectElement.closest('.form-row');
    if (!row) return;

    selectElement.value = '';

    const stockInput = row.querySelector('input[name$="-stock"]');
    if (stockInput) {
        clearStockValue(stockInput);
    }

    const quantityInput = row.querySelector('input[name$="-quantity"]');
    if (quantityInput) {
        quantityInput.value = '';
        quantityInput.max = null;
        quantityInput.placeholder = '';
    }

    selectElement.removeAttribute('data-supply-code');
    selectElement.removeAttribute('data-supply-name');
    selectElement.removeAttribute('data-supply-stock');
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function initializeAddButton(container, totalForms) {
    const addButton = document.getElementById('add-form');
    if (!addButton) return;

    addButton.addEventListener('click', function () {
        addNewFormRow(container, totalForms);
    });
}

function addNewFormRow(container, totalForms) {
    const formCount = parseInt(totalForms.value);
    const template = document.getElementById('empty-form-template');

    if (!template) {
        console.error('Empty form template not found');
        return;
    }

    let newRowHtml = template.innerHTML.replace(/__prefix__/g, formCount);

    newRowHtml = newRowHtml.replace(
        /id="([^"]*)"/g,
        (match, id) => `id="${id.replace(/__prefix__/g, formCount)}"`
    );

    container.insertAdjacentHTML('beforeend', newRowHtml);
    totalForms.value = formCount + 1;

    const lastRow = container.lastElementChild;

    const newSelect = lastRow.querySelector('select[name$="-supply"]');
    if (newSelect) {
        initializeSelect2WithAjax(newSelect, formCount);
    }

    // Disparar evento personalizado
    const event = new CustomEvent('formRowAdded', {
        detail: {row: lastRow, formIndex: formCount}
    });
    container.dispatchEvent(event);
}

function initializeRemoveHandler(container, totalForms) {
    container.addEventListener('click', function (e) {
        const deleteButton = e.target.closest('.remove-row');
        if (!deleteButton) return;

        e.preventDefault();
        removeFormRow(deleteButton, container, totalForms);
    });
}

function removeFormRow(deleteButton, container, totalForms) {
    const row = deleteButton.closest('.form-row');
    if (!row) return;

    // Destruir instancia de Select2 antes de eliminar
    const select = row.querySelector('select[name$="-supply"]');
    if (select && typeof $ !== 'undefined' && $.fn.select2) {
        $(select).select2('destroy');
    }

    const deleteCheckbox = row.querySelector('input[type="checkbox"][name$="-DELETE"]');

    if (deleteCheckbox) {
        deleteCheckbox.checked = true;
        row.style.display = 'none';
    } else {
        row.remove();
        totalForms.value = parseInt(totalForms.value) - 1;

        // Renumerar los índices de los formularios restantes
        renumberFormIndexes(container);
    }
}

function renumberFormIndexes(container) {
    const rows = container.querySelectorAll('.form-row:not([style*="display: none"])');

    rows.forEach((row, index) => {
        // Actualizar todos los campos name e id
        const elements = row.querySelectorAll('[name*="-"], [id*="-"]');
        elements.forEach(element => {
            if (element.name) {
                element.name = element.name.replace(/movement_set-\d+-/, `movement_set-${index}-`);
            }
            if (element.id) {
                element.id = element.id.replace(/movement_set-\d+-/, `movement_set-${index}-`);
            }
        });

        // Reinicializar Select2 con el nuevo índice
        const select = row.querySelector('select[name$="-supply"]');
        if (select && typeof $ !== 'undefined' && $.fn.select2) {
            initializeSelect2WithAjax(select, index);
        }
    });
}

function updateStockField(stockInput, value) {
    if (!stockInput) return;

    stockInput.value = value;
    stockInput.classList.add('stock-updated');

    // Feedback visual
    const originalColor = stockInput.style.backgroundColor;
    stockInput.style.backgroundColor = '#d4edda';

    setTimeout(() => {
        stockInput.classList.remove('stock-updated');
        stockInput.style.backgroundColor = originalColor;
    }, 500);
}

function clearStockValue(stockInput) {
    if (!stockInput) return;
    stockInput.value = '';
}

// Funciones utilitarias exportadas
window.FormsetHelper = {
    addNewFormRow,
    removeFormRow,
    getSelectedSupplyIds: function (container) {
        const selects = container.querySelectorAll('select[name$="-supply"]');
        return Array.from(selects)
            .filter(select => select.value)
            .map(select => select.value);
    },
    hasDuplicateSupplies: function (container) {
        const selectedIds = this.getSelectedSupplyIds(container);
        return selectedIds.length !== new Set(selectedIds).size;
    },
    resetFormset: function (container, totalForms) {
        // Destruir todas las instancias de Select2
        const allSelects = container.querySelectorAll('select[name$="-supply"]');
        allSelects.forEach(select => {
            if (typeof $ !== 'undefined' && $.fn.select2 && $(select).data('select2')) {
                $(select).select2('destroy');
            }
        });

        const rows = container.querySelectorAll('.form-row');
        rows.forEach(row => row.remove());
        totalForms.value = 1;
        this.addNewFormRow(container, totalForms);
    },
    exportFormsetData: function (container) {
        const rows = container.querySelectorAll('.form-row');
        const data = [];

        rows.forEach(row => {
            const deleteCheckbox = row.querySelector('input[type="checkbox"][name$="-DELETE"]');
            if (deleteCheckbox && deleteCheckbox.checked) return;

            const supplySelect = row.querySelector('select[name$="-supply"]');
            const quantityInput = row.querySelector('input[name$="-quantity"]');

            if (supplySelect && supplySelect.value) {
                data.push({
                    supply_code: supplySelect.value,
                    supply_name: supplySelect.getAttribute('data-supply-name') || '',
                    quantity: quantityInput ? parseInt(quantityInput.value) || 0 : 0
                });
            }
        });

        return data;
    }
};