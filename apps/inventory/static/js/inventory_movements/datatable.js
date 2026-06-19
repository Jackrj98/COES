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
            {selector: "#id_movement_type", field: "movement_type"},
            {selector: "#id_date_from", field: "created_at", type: "date-range"}
        ],
        paginationClass: "pagination-primary"
    });
    table.init();
});

const columns = [
    {
        orderable: false,
        data: "movement_type",
        width: "12%",
        className: DataTableFactory.classes.center,
        render: (data, type, row) => {
            const config = mapTypeChoices[data] || {
                color: 'secondary',
                label: 'Desconocido',
                icon: 'bi-question-circle'
            };

            return `
                    <td class="py-4">
                        <div class="d-flex align-items-center gap-3" 
                                data-bs-toggle="tooltip" 
                                data-bs-placement="top"
                                data-bs-original-title="${config.label}">
                            <div class="bg-${config.color} bg-opacity-25 rounded-3 d-flex align-items-center justify-content-center flex-shrink-0"
                                 style="width: 40px; height: 40px;">
                                <span class="font-bold fs-6 text-secondary">
                                <i class="${config.icon} text-${config.color}"></i>
                            </div>
                            <div class="font-bold">${config.label}</div>
                        </div>
                    </td>`;
        }
    },
    {
        orderable: false,
        data: "batch__batch_number",
        width: "22%",
        className: DataTableFactory.classes.justify,
        render: (data, type, row) => {
            const {batch__supply__name: supplyName, batch__supply__code: supplyCode} = row;
            return `
                <td class="py-4">
                    <div class="d-flex align-items-center gap-3" 
                        data-bs-toggle="tooltip" 
                        data-bs-placement="top"
                        data-bs-original-title="${supplyName} (${supplyCode})">
                        
                        <a href="" class="text-decoration-none text-reset d-block">
                            <div class="text-start">
                                <div class="font-bold">${supplyName}</div>
                                <div class="small text-muted text-uppercase" style="font-size: 0.75rem; letter-spacing: 0.05em;">
                                    ${data}
                                </div>
                            </div>
                        </a>
                    </div>
                </td>`;
        }
    },
    {
        orderable: false,
        data: "concept",
        width: "22%",
        className: DataTableFactory.classes.justify
    },
    {
        orderable: false,
        data: "quantity",
        width: "10%",
        className: DataTableFactory.classes.center,
        render: (data, type, row) => {
            const isIncrement = !!row.is_increment;

            const icon = isIncrement ? 'bi-arrow-up-right' : 'bi-arrow-down-right';
            const colorClass = isIncrement ? 'text-success' : 'text-danger';
            const formatData = isIncrement ? `+ ${data}` : `- ${data}`;

            return `
                <div class="${colorClass} fw-bold">
                    <i class="bi ${icon} me-2" style="font-weight: 900;"></i>   
                    ${formatData}
                </div>`;
        }
    },
    {
        orderable: false,
        data: "previous_stock",
        width: "10%",
        className: DataTableFactory.classes.center,
        render: (data, type, row) => {
            const afterStock = row.after_stock || 0;
            return `
                <div class="fw-light">
                    ${data}
                    <i class="bi bi-arrow-right" style="font-weight: 900;"></i>   
                    <span class="fw-bold">${afterStock}</span>
                </div>`;
        }
    },
    {
        orderable: false,
        data: "status",
        width: "10%",
        className: DataTableFactory.classes.center,
        render: (data) => {
            const {color, label} = mapStatus[data];
            return `
               <td class="py-4">
                    <span class="text-truncate bg-${color} bg-opacity-25 rounded-pill px-3 
                            d-inline-block text-center w-100"
                          data-bs-toggle="tooltip"
                          data-bs-placement="top"
                          data-bs-original-title="${label}">
                        <span class="fw-semibold text-${color}">${label}</span>
                    </span>
                </td>
            `
        }
    },
    {
        orderable: false,
        data: "created_at",
        width: "10%",
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
        render: (data) => `
            <td class="py-4">
                <div class="d-flex justify-content-center">
                    <button type="button" class="btn btn-icon btn-outline-secondary rounded-circle border-0" 
                            onclick="window.location.href='${urlPaginator}${data}/'">
                        <i class="bi bi-eye fs-6"></i>
                    </button>
                </div>
            </td>`
    }
];