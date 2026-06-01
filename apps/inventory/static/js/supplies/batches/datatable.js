$(document).ready(function () {
    if (!urlPaginator || urlPaginator === "None") {
        console.error("Error: urlPaginator no está definido. Revisa la View en Django.");
        return;
    }

    const table = new DataTableFactory({
        selector: "#datatable-list",
        ajaxUrl: urlPaginator,
        columns: columns,
        order: [[2, "desc"]],
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
        data: "days_until_expiry",
        width: "4%",
        className: DataTableFactory.classes.center,
        render: (days) => {
            let color = "";
            let text = "";

            if (days < 0) {
                color = "text-danger";
                text = "Vencido";
            } else if (days <= 30) {
                color = "text-warning";
                text = "Por vencer";
            } else {
                color = "text-success";
                text = "Vigente";
            }

            return `
                <div class="d-flex align-items-center justify-content-center" data-bs-toggle="tooltip" title="${text}">
                    <i class="bi bi-circle-fill ${color}" style="font-size: 0.75rem;"></i>
                </div>
            `;
        }
    },
    {
        orderable: false,
        data: "number",
        width: "20%",
        className: DataTableFactory.classes.justify
    },
    {
        orderable: false,
        data: "due_date",
        width: "20%",
        className: DataTableFactory.classes.center,
        render: (data, type, row) => {
            const {full} = parseDateTime(data);
            const days = row.days_until_expiry;

            let badgeClass = "";
            let badgeText = "";

            if (days < 0) {
                badgeClass = "bg-danger bg-opacity-10 text-danger";
                badgeText = "Vencido";
            } else if (days <= 30) {
                badgeClass = "bg-warning bg-opacity-10 text-warning";
                badgeText = `${days}d restantes`;
            } else {
                badgeClass = "bg-success bg-opacity-10 text-success";
                badgeText = `${days}d restantes`;
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
        data: "stock",
        width: "10%",
        className: DataTableFactory.classes.center
    },
    {
        orderable: false,
        data: "total_supply_stock",
        width: "10%",
        className: DataTableFactory.classes.justify,
        render: (data, type, row) => {
            const isInactive = row.status !== 1;
            const batchStock = isInactive ? 0 : (row.stock || 0);
            const totalSupplyStock = row.total_supply_stock || 0;

            const percentage = (totalSupplyStock > 0 && !isInactive)
                ? Math.round((batchStock / totalSupplyStock) * 100)
                : 0;

            return `
                <div class="d-flex align-items-center" style="gap: 10px;">
                    <div class="progress flex-grow-1" style="height: 6px; background-color: #2d3748; border-radius: 3px;">
                        <div class="progress-bar" role="progressbar" 
                             style="width: ${percentage}%; background-color: ${isInactive ? '#4a5568' : '#6366f1'}; border-radius: 3px;">
                        </div>
                    </div>
                    <span class="text-muted small" style="min-width: 35px; text-align: right;">${percentage}%</span>
                </div>
            `;
        }
    },
    {
        orderable: false,
        data: "purchase_unit_cost",
        width: "10%",
        className: DataTableFactory.classes.center,
        render: (data) => "$" + (data || "0")
    },
    {
        orderable: false,
        data: "purchase_order__order_number",
        width: "12%",
        className: DataTableFactory.classes.center,
        render: (data, type, row) => {
            const order_number = data || " - ";
            const detailUrl = `${urlPaginator}${row.purchase_order__external_id}/`;

            return `
                <td class="py-4">
                    <a href="${detailUrl}" 
                       class="font-bold text-primary" 
                       data-bs-toggle="tooltip" 
                       data-bs-placement="top">
                        <span class="d-inline-block text-truncate" style="max-width: 100%;">
                            ${order_number}
                        </span>
                    </a>
                </td>
            `
        }
    },
    {
        orderable: false,
        data: "status",
        width: "15%",
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