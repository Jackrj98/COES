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
            {selector: "#id_date_from", field: "created_at", type: "date-range"},
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
        width: "10%",
        className: DataTableFactory.classes.justify,
        render: (data, type, row) => {
            const detailUrl = `${urlPaginator}${row.external_id}/`;
            return `
                <a href="${detailUrl}" 
                   class="text-decoration-none fw-semibold" 
                   data-bs-toggle="tooltip" 
                   data-bs-placement="top" 
                   title="Ver detalles">
                    <span class="d-inline-block text-truncate" style="max-width: 100%;">
                        ${data}
                    </span>
            `
        }
    },
    {
        orderable: false,
        data: "supplier__business_name",
        width: "25%",
        className: DataTableFactory.classes.justify,
        render: (data, type, row) => {
            return `
                <span class="text-truncate" style="max-width: 100%;">
                    ${data}
                </span>
                <small class="text-muted d-block">${row.supplier__contact_name}</small>
            `;
        }
    },
    {
        orderable: false,
        data: "status",
        width: "12%",
        className: DataTableFactory.classes.center,
        render: (data) => {
            const {color, label} = statusChoices[data];
            return `
                <span class="text-truncate bg-${color} bg-opacity-25 rounded-pill px-3 
                            d-inline-block text-center w-100"
                          data-bs-toggle="tooltip"
                          data-bs-placement="top"
                          data-bs-original-title="${label}">
                        <span class="fw-semibold text-${color}">${label}</span>
                </span>`;
        }
    },
    {
        orderable: false,
        data: "estimated_delivery",
        width: "12%",
        className: DataTableFactory.classes.center,
        render: (data) => {
            const {full, time} = parseDateTime(data);
            return `
                <div class="d-flex flex-column align-items-end gap-2">
                    <small class="text-muted">${full}</small>
                </div>
            `;
        }
    },
    {
        orderable: false,
        data: "actual_delivery",
        width: "12%",
        className: DataTableFactory.classes.center,
        render: (data) => {
            const {full, time} = parseDateTime(data);
            return `
                <div class="d-flex flex-column align-items-end gap-2">
                    <small class="text-muted">${full}</small>
                </div>
            `;
        }
    },
    {
        orderable: false,
        data: "items",
        width: "8%",
        className: DataTableFactory.classes.center,
        render: (data) => {
            return `
                <span class="text-truncate bg-primary bg-opacity-25 rounded-pill px-3 
                            d-inline-block text-center w-100"
                          data-bs-toggle="tooltip"
                          data-bs-placement="top"
                          data-bs-original-title="${data} ítems">
                        <span class="fw-semibold text-primary">${data} ítems</span>
                </span>
            `;
        }
    },
    {
        orderable: true,
        data: "created_at",
        width: "14%",
        className: DataTableFactory.classes.justify,
        render: (data, type, row) => {
            const {full, time} = parseDateTime(data);
            return `
                <div class="d-flex flex-column align-items-end gap-2">
                    <small class="text-muted">${full}</small>
                    <small class="text-muted">${time}</small>
                </div>
            `;
        }
    },
    {
        data: "external_id",
        width: "7%",
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

