$(document).ready(function () {
    if (!urlPaginator || urlPaginator === "None") {
        console.error("Error: urlPaginator no está definido. Revisa la View en Django.");
        return;
    }

    const table = new DataTableFactory({
        selector: "#datatable-list",
        ajaxUrl: urlPaginator,
        columns: columns,
        order: [],
        filters: [
            {selector: "#id_status", field: "status"},
            {selector: "#id_search", field: "search"},
        ],
        paginationClass: "pagination-primary"
    });
    table.init();
});


const columns = [
    {
        orderable: false,
        data: "order_number",
        width: "22%",
        className: DataTableFactory.classes.justify
    },
    {
        orderable: false,
        data: "motive",
        width: "12%",
        className: DataTableFactory.classes.center,
        render: (data) => `<span class="fw-mono">${data || '—'}</span>`
    },
    {
        orderable: false,
        data: "requested_by",
        width: "2%",
        className: DataTableFactory.classes.center
    },
    {
        orderable: false,
        data: "items",
        width: "4%",
        className: DataTableFactory.classes.center
    },
    {
        orderable: false,
        data: "total",
        width: "12%",
        className: DataTableFactory.classes.center,
        render: (data) => {
            const value = parseFloat(data);
            if (!isNaN(value)) {
                return `<span class="fw-mono">$${value.toFixed(2)}</span>`;
            }
            return `<span class="fw-mono">-</span>`;
        }
    },
    {
        orderable: false,
        data: "status",
        width: "14%",
        className: DataTableFactory.classes.center,
        render: (data) => {
            const status = data ? 1 : 0;
            const label = statusChoices[status];
            const color = statusColorChoices[status];
            const icon = data ? 'bi-toggle-on' : 'bi-toggle-off';

            return `
                <span class="text-truncate bg-${color} bg-opacity-25 rounded-pill px-3 
                            d-inline-block text-center w-100"
                          data-bs-toggle="tooltip"
                          data-bs-placement="top"
                          data-bs-original-title="${label}">
                        <span class="fw-semibold text-${color}">${label}</span>
                    </span>
            `;
        }
    },
    {
        orderable: true,
        data: "created_at",
        width: "14%",
        className: DataTableFactory.classes.center,
        render: (data, type, row) => {
            const {full} = parseDateTime(data);
            return `
                <div class="d-flex flex-column align-items-end gap-2">
                    <small class="text-muted">${full}</small>
                </div>
            `;
        }
    },
    {
        data: "external_id",
        width: "4%",
        orderable: false,
        className: DataTableFactory.classes.center,
        render: (data, type, row) => {
            const detailUrl = `${urlPaginator}${data}/`;
            const editUrl = `${urlPaginator}${data}/update`;
            const statusUrl = `${urlPaginator}${data}/update-status/`;

            return `
                <div class="d-flex justify-content-center gap-1">                    
                    <button type="button" class="btn btn-icon icon-left btn-outline-secondary bg-opacity-25 rounded-circle border-0" 
                            data-bs-toggle="tooltip" 
                            data-bs-placement="top" 
                            title="Ver detalles" 
                            onclick="window.location.href='${detailUrl}'">
                        <i class="bi bi-eye fs-6"></i>
                    </button>
                </div>
            `;
        }
    }
];

