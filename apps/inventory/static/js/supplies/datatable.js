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
            {selector: "#id_stock", field: "stock"},
            {selector: "#id_category", field: "category"},
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
        data: "name",
        width: "22%",
        className: DataTableFactory.classes.justify,
        render: (data, type, row) => {
            const detailUrl = `${urlPaginator}${row.external_id}/`;
            const initials = n => n.split(' ').slice(0, 2).map(w => w[0]).join('').toUpperCase();

            return `
                    <td class="py-4">
                        <div class="d-flex align-items-center gap-3" 
                                data-bs-toggle="tooltip" 
                                data-bs-placement="top"
                                data-bs-original-title="${row.description}">
                            <div class="bg-secondary bg-opacity-25 rounded-3 d-flex align-items-center justify-content-center flex-shrink-0"
                                 style="width: 40px; height: 40px;">
                                <span class="font-bold fs-6 text-secondary">${initials(data)}</span>
                            </div>
                            <a href="${detailUrl}" class="text-decoration-none text-reset d-block">
                                <div class="text-start">
                                    <div class="font-bold">${data}</div>
                                    <div class="small text-muted text-uppercase" style="font-size: 0.75rem; letter-spacing: 0.05em;">${row.code}</div>
                                </div>
                            </a>
                        </div>
                    </td> 
            `;
        }
    },
    {
        orderable: false,
        data: "category__name",
        width: "10%",
        className: DataTableFactory.classes.center,
        render: (data, type, row) => {
            return `
                    <span class="badge bg-secondary bg-opacity-10 text-secondary rounded-pill py-2" style="width: 10vw">
                        ${data}
                    </span>`;
        }
    },
    {
        orderable: false,
        data: "unit_of_measure__name",
        width: "10%",
        className: DataTableFactory.classes.center,
        render: (data, type, row) => {
            const unit = row.unit_of_measure__extra || " - ";

            return `
                    <td class="py-4">
                         <div class="font-semibold">${data}</div>
                         <div class="small text-muted text-uppercase" style="font-size: 0.75rem; letter-spacing: 0.05em;">${unit}</div>
                    </td>
                `
        }
    },
    {
        orderable: false,
        data: "stock",
        width: "10%",
        className: DataTableFactory.classes.justify,
        render: (data, type, row) => {
            const stock = data || 0;
            const min = row.stock_min || 1;

            const stockColor = (s, m) => {
                if (s <= m) return '#ef4444';
                if (s <= m * 1.5) return '#f59e0b';
                return '#22c55e';
            };

            const col = stockColor(stock, min);

            const maxReference = min * 1.5;
            const pct = Math.min(Math.round((stock / maxReference) * 100), 100);

            return `
                    <div class="d-flex flex-column" style="width: 80px;">
                        <span class="fw-bold mb-1" style="color: ${col}; font-size: 0.9rem;">
                            ${stock}
                        </span>
                        <div class="progress" style="height: 6px; background-color: #2b3035;">
                            <div class="progress-bar" 
                                 role="progressbar" 
                                 style="width: ${pct}%; background-color: ${col};">
                            </div>
                        </div>
                    </div>
                `;

        }
    },
    {
        orderable: false,
        data: "stock_min",
        width: "5%",
        className: DataTableFactory.classes.center
    },
    {
        orderable: false,
        data: "stock_max",
        width: "5%",
        className: DataTableFactory.classes.center
    },
    {
        orderable: false,
        data: "stock",
        width: "10%",
        className: DataTableFactory.classes.center,
        render: (data, type, row) => {
            const stock = data || 0;
            const min = row.stock_min || 1;

            let badgeClass = '';
            let badgeText = '';
            let tooltipText = `Stock actual: ${stock} | Mínimo requerido: ${min}`;

            // Lógica actualizada:
            if (stock <= min) {
                badgeClass = 'bg-danger bg-opacity-10 text-danger';
                badgeText = 'Stock crítico';
                tooltipText += ' | ¡Acción requerida!';
            } else if (stock <= min * 1.5) {
                badgeClass = 'bg-warning bg-opacity-10 text-warning';
                badgeText = 'Stock bajo';
                tooltipText += ' | Cerca del mínimo';
            } else {
                badgeClass = 'bg-success bg-opacity-10 text-success';
                badgeText = 'Stock normal';
                tooltipText += ' | Nivel óptimo';
            }

            return `
                    <span class="badge ${badgeClass} rounded-pill py-2 px-3" 
                          style="min-width: 90px;" 
                          title="${tooltipText}"
                          data-bs-toggle="tooltip">
                        ${badgeText}
                    </span>`;
        }
    },
    {
        data: "external_id",
        width: "4%",
        orderable: false,
        className: DataTableFactory.classes.center,
        render: (data, type, row) => {
            const detailUrl = `${urlPaginator}${data}/`;
            return `
                   <td class="py-4">
                        <div class="d-flex justify-content-center gap-1">
                            <button type="button" class="btn btn-icon icon-left btn-outline-secondary bg-opacity-25 rounded-circle border-0"
                                    data-bs-toggle="tooltip"
                                    data-bs-placement="top"
                                    title="Ver detalles"
                                    onclick="window.location.href='${detailUrl}'">
                                <i class="bi bi-eye fs-6"></i>
                            </button>
                        </div>
                    </td>
                `;
        }
    }
];