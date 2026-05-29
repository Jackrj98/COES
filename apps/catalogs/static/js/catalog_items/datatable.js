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
            {selector: "#id_reason", field: "reason"},
            {selector: "#id_delivery_days", field: "delivery_days"},
        ],
        paginationClass: "pagination-primary"
    });
    table.init();
});


const columns = [
    {
        orderable: true,
        data: "priority",
        width: "4%",
        className: DataTableFactory.classes.center,
        render: (data) => `<span class="fw-mono">${data || '—'}</span>`
    },
    {
        orderable: false,
        data: "name",
        width: "22%",
        className: DataTableFactory.classes.justify,
        render: (data, type, row) => {
            const detailUrl = `${urlPaginator}${row.external_id}/`;
            const description = row.description ? row.description.replace(/"/g, '&quot;') : '';

            return `
            <a href="${detailUrl}" 
               class="text-decoration-none text-reset fw-semibold" 
               data-bs-toggle="tooltip" 
               data-bs-placement="top" 
               title="${description}">
                <span class="d-inline-block text-truncate" style="max-width: 100%;">
                    ${data}
                </span>
            </a>
        `;
        }
    },
    {
        orderable: false,
        data: "code",
        width: "12%",
        className: DataTableFactory.classes.center,
        render: (data) => {
            return `
                 <div class="d-flex flex-column" style="max-width: 12vw; min-width: 0;">
                    <span class="text-truncate bg-secondary bg-opacity-25 rounded-pill px-3 py-1 
                        d-inline-block text-center w-100" 
                            data-bs-toggle="tooltip" 
                            data-bs-placement="top" 
                            title="${data || '-'}">
                        <span class="fw-semibold text-secondary">${data || '-'}</span>
                    </span>
                </div>
            `;
        }
    },
   {
        orderable: false,
        data: "extra",
        width: "8%",
        className: DataTableFactory.classes.center,
        render: (data) => {
            return `
                 <div class="d-flex flex-column" style="max-width: 12vw; min-width: 0;">
                    <span class="text-truncate bg-secondary bg-opacity-25 rounded-pill px-3 py-1 
                        d-inline-block text-center w-100" 
                            data-bs-toggle="tooltip" 
                            data-bs-placement="top" 
                            title="${data || '-'}">
                        <span class="fw-semibold text-secondary">${data || '-'}</span>
                    </span>
                </div>
            `;
        }
    },
    {
        orderable: false,
        data: "is_active",
        width: "14%",
        className: DataTableFactory.classes.center,
        render: (data) => {
            const status = data ? 1 : 0;
            const label = statusChoices[status];
            const color = statusColorChoices[status];
            const icon = data ? 'bi-toggle-on' : 'bi-toggle-off';

            return `
                <span class="bg-${color} bg-opacity-25 rounded-pill px-3 py-1 d-inline-block text-center w-100">
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

            return `
                <div class="d-flex justify-content-center gap-1">                    
                    <button type="button" class="btn btn-icon icon-left btn-outline-secondary bg-opacity-25 rounded-circle border-0" 
                            data-bs-toggle="tooltip" 
                            data-bs-placement="top" 
                            title="Ver detalles" 
                            onclick="window.location.href='${detailUrl}'">
                        <i class="bi bi-eye fs-6"></i>
                    </button>
                    
                    <button type="button" class="btn btn-icon icon-left btn-outline-secondary bg-opacity-25 rounded-circle border-0" 
                            data-bs-toggle="tooltip" 
                            data-bs-placement="top" 
                            title="Editar detalles" 
                            onclick="window.location.href='${editUrl}'">
                        <i class="bi bi-pencil-square fs-6"></i>
                    </button>
                </div>
            `;
        }
    }
];