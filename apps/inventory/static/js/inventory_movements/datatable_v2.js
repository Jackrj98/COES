$(document).ready(function () {
    if (!urlPaginator || urlPaginator === "None") {
        console.error("Error: urlPaginator no está definido. Revisa la View en Django.");
        return;
    }

    const table = new DataTableFactory({
        selector: "#datatable-list",
        ajaxUrl: urlPaginator,
        columns: columns,
        order: [[0, "asc"]],
        filters: [
            {selector: "#id_status", field: "status"},
            {selector: "#id_search", field: "search"},
            {selector: "#id_movement_type", field: "movement_type"},
            {selector: "#id_date_from", field: "created_at", type: "date-range"}
        ],
        paginationClass: "pagination-primary",
        footerCallback: (table, row, data, start, end, display) => {
            let totalIncrement = 0;
            let totalDecrement = 0;

            for (let i = start; i < end; i++) {
                const item = data[i];
                if (item.is_increment) {
                    totalIncrement += item.quantity;
                } else {
                    totalDecrement += item.quantity;
                }
            }

            const netBalance = totalIncrement - totalDecrement;
            const api = table.api();
            $(api.column(4).footer()).html(`<span class="text-success fw-bold">+${totalIncrement}</span>`);
            $(api.column(5).footer()).html(`<span class="text-danger fw-bold">-${totalDecrement}</span>`);
            $(api.column(6).footer()).html(`
        <span class="fw-bold text-${netBalance >= 0 ? 'success' : 'danger'}">
            ${netBalance >= 0 ? '+' : ''}${netBalance.toLocaleString()}
        </span>
    `);
        }
    });
    table.init();
});


const columns = [
    {
        data: "created_at", width: "10%", className: DataTableFactory.classes.center,
        render: (data) => data ? `<small class="text-muted">${parseDateTime(data).full}</small>` : '---'
    },
    {
        orderable: false,
        data: "movement_type", width: "12%",
        render: (data, type, row) => {
            const config = mapTypeChoices[data] || {
                color: 'secondary',
                label: 'Desconocido',
                icon: 'bi-question-circle'
            };

            return `
                <div class="d-flex align-items-center gap-3" 
                    data-bs-toggle="tooltip" 
                    data-bs-placement="top"
                    data-bs-original-title="${config.label}">
                    <div class="bg-${config.color} bg-opacity-25 rounded-3 d-flex align-items-center justify-content-center flex-shrink-0"
                        style="width: 30px; height: 30px;">
                        <span class="fw-lighter fs-6 text-secondary">
                            <i class="${config.icon} text-${config.color}"></i>
                    </div>
                    <div class="fw-lighter">${config.label}</div>
                </div>`;
        }
    },
    {
        orderable: false,
        data: "batch__batch_number", width: "20%",
        render: (data, type, row) => {
            if (!row.batch__supply__name) return '<span class="text-muted fst-italic">N/A</span>';
            return `
            <div class="text-start">
                <div class="font-bold">${row.batch__supply__name}</div>
                <div class="small text-muted text-uppercase">${data || '---'}</div>
            </div>`;
        }
    },
    {
        orderable: false,
        data: "concept", width: "15%"
    },
    {
        orderable: false,
        data: "quantity", width: "8%", className: DataTableFactory.classes.center,
        render: (data, type, row) => row.is_increment ? `<span class="text-success fw-bold">+${data}</span>` : '<span class="text-muted">—</span>'
    },
    {
        orderable: false,
        data: "quantity", width: "8%", className: DataTableFactory.classes.center,
        render: (data, type, row) => !row.is_increment ? `<span class="text-danger fw-bold">-${data}</span>` : '<span class="text-muted">—</span>'
    },
    {
        orderable: false,
        data: "after_stock", width: "8%", className: DataTableFactory.classes.center,
        render: (data) => `<span class="fw-bold">${data ?? 0}</span>`
    },
    {
        orderable: false,
        data: "external_id", width: "7%", className: DataTableFactory.classes.center,
        render: (data, type, row) => {
            const order = row.inventory_order__order_number || "-";
            return  order ? `<small class="font-monospace text-muted">${order}</small>` : '<span class="text-muted">—</span>'
        }
    },
    {
        orderable: false,
        data: "status", width: "7%", className: DataTableFactory.classes.center,
        render: (data) => {
            if (!data) return '<span class="text-muted">—</span>';
            const {color, label} = mapStatus[data] || {color: 'secondary', label: 'N/A'};
            return `<span class="badge bg-${color} bg-opacity-25 text-${color} rounded-pill">${label}</span>`;
        }
    },
    {
        orderable: false,
        data: "created_by", width: "5%", className: DataTableFactory.classes.center,
        render: (data) => data ? `<span class="text-muted font-italic">${data}</span>` : '---'
    }
];