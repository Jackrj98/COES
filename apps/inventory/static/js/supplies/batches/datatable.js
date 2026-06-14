$(document).ready(function () {
    if (!urlPaginator || urlPaginator === "None") {
        console.error("Error: urlPaginator no está definido. Revisa la View en Django.");
        return;
    }

    const table = new DataTableFactory({
        selector: "#datatable-list",
        ajaxUrl: urlPaginator,
        columns: columns,
        order: [[2, "asc"], [5, "asc"]],
        filters: [
            {selector: "#id_status", field: "status"},
            {selector: "#id_search", field: "search"},
            {selector: "#id_expiration", field: "expiration"},
        ],
        paginationClass: "pagination-primary"
    });
    table.init();
});

const columns = [
    {
        orderable: false,
        data: "external_id",
        width: "3%",
        className: DataTableFactory.classes.center,
        render: (data, type, row, meta) => {
            return meta.settings._iDisplayStart + meta.row + 1;
        }
    },
    {
        orderable: false,
        data: "batch_number",
        width: "20%",
        className: DataTableFactory.classes.justify,
        render: (data, type, row) => {
            const days = row.days_until_expiry;
            let color = "";
            let text = "";
            const months = Math.floor(days / 30.44);

            if (days < 0) {
                color = "text-secondary";
                text = "Vencido";
            } else if (months <= 6) {
                color = "text-danger";
                text = "Corto plazo";
            } else if (months <= 12) {
                color = "text-warning";
                text = "Atención";
            } else {
                color = "text-success";
                text = "Activo";
            }

            return `
                <div class="d-flex align-items-justify justify-content-justify" data-bs-toggle="tooltip" title="${text}">
                    <i class="bi bi-circle-fill ${color} me-2" style="font-size: 0.75rem;"></i> ${data}
                </div>`;
        }
    },
    {
        orderable: true,
        data: "expiry_date",
        width: "20%",
        className: DataTableFactory.classes.center,
        render: (data, type, row) => {
            const {full} = parseDateTime(data);
            const days = row.days_until_expiry;

            let badgeClass = "";
            let badgeText = "";

            const months = Math.floor(days / 30.44);
            const timeDisplay = days < 30
                ? `${days} días restantes`
                : `${months} meses restantes`;

            if (days < 0) {
                badgeClass = "bg-danger bg-opacity-10 text-danger";
                badgeText = "Vencido";
            } else if (months <= 6) {
                badgeClass = "bg-danger bg-opacity-10 text-danger";
                badgeText = timeDisplay;
            } else if (months <= 12) {
                badgeClass = "bg-warning bg-opacity-10 text-warning";
                badgeText = timeDisplay;
            } else {
                badgeClass = "bg-success bg-opacity-10 text-success";
                badgeText = timeDisplay;
            }

            return `
                <div class="d-flex flex-column align-items-center gap-1">
                    <span class="text-white font-bold" style="font-size: 0.85rem;">${full}</span>
                    <span class="badge rounded-pill px-2 ${badgeClass}" style="font-size: 0.70rem;">
                        ${badgeText}
                    </span>
                </div>`;
        }
    },
    {
        orderable: false,
        data: "current_quantity",
        width: "12%",
        className: DataTableFactory.classes.center,
        render: (data, type, row) => {
            const initialQty = row.initial_quantity || 0;
            const currentQty = row.current_quantity || 0;
            const isInactive = row.status !== 1;

            const batchStock = isInactive ? 0 : currentQty;
            const percentage = (initialQty > 0)
                ? Math.min(Math.round((batchStock / initialQty) * 100), 100)
                : 0;

            let progressColor = '#0d6efd';
            if (isInactive) {
                progressColor = '#6c757d';
            } else if (percentage < 20) {
                progressColor = '#dc3545';
            } else if (percentage < 50) {
                progressColor = '#0dcaf0';
            }

            return `
                <div class="d-flex flex-column" style="line-height: 1.2;">
                    <div class="fw-bold" style="font-size: 1.05rem;">
                        ${isInactive ? '0' : data} 
                        <small class="text-muted fw-normal" style="font-size: 0.8rem;">/ ${initialQty}</small>
                    </div>
                    <div class="d-flex align-items-center mt-1" style="gap: 6px;">
                        <div class="progress flex-grow-1" style="height: 5px; background-color: #e9ecef; border-radius: 2px;">
                            <div class="progress-bar" role="progressbar" 
                                 style="width: ${percentage}%; background-color: ${progressColor}; border-radius: 2px;">
                            </div>
                        </div>
                        <span class="text-muted" style="font-size: 0.75rem; min-width: 30px; text-align: right;">${percentage}%</span>
                    </div>
                </div>`;
        }
    },
    {
        orderable: false,
        data: "unit_cost",
        width: "10%",
        className: DataTableFactory.classes.center,
        render: (data) => "$" + (data || "0")
    },
    {
        orderable: true,
        data: "status",
        width: "12%",
        className: DataTableFactory.classes.center,
        render: (data) => {
            const {color, label} = mapStatus[data];
            return `
                <span class="badge bg-${color} bg-opacity-10 text-${color} rounded-pill py-2" style="width: 9vw">
                    ${label}
                </span>
            `
        }
    },
    {
        data: "external_id",
        width: "10%",
        orderable: false,
        className: DataTableFactory.classes.center,
        render: (data) => `
            <td class="py-4">
                <div class="d-flex justify-content-center">
                    <button type="button" class="btn btn-icon btn-outline-secondary rounded-circle border-0" 
                            onclick="window.location.href='${urlPaginator}${data}/'">
                        <i class="bi bi-eye fs-6"></i>
                    </button>
                    <button type="button" class="btn btn-icon btn-outline-secondary rounded-circle border-0" 
                            onclick="window.location.href='${urlPaginator}${data}/update'">
                        <i class="bi bi-pencil-square fs-6"></i>
                    </button>
                </div>
            </td>`
    }
];