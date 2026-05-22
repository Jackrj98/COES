$(document).ready(function () {
    if (!urlPaginator || urlPaginator === "None") {
        console.error("Error: urlPaginator no está definido. Revisa la View en Django.");
        return;
    }

    const userTable = new DataTableFactory({
        selector: "#datatable-list",
        ajaxUrl: urlPaginator,
        columns: userColumns,
        filters: [
            {selector: "#id_date_from", field: "created_at", type: "date-range"},
            {selector: "#id_status", field: "status"},
            {selector: "#id_search", field: "search"}
        ],
        order: [[6, "desc"]],
        paginationClass: "pagination-primary"
    });
    userTable.init();
});


const userColumns = [
    {
        orderable: false,
        data: "external_id",
        width: "5%",
        className: DataTableFactory.classes.center,
        render: (data, type, row, meta) => {
            return meta.settings._iDisplayStart + meta.row + 1;
        }
    },
    {
        orderable: false,
        data: "email",
        width: "20%",
        className: DataTableFactory.classes.justify,
        render: (data, type, row) => {
            let {person__last_name: lastName, person__first_name: firstName, email_verified: emailVerified} = row;
            const fullName = lastName ? `${firstName} ${lastName}`.trim() : "-";
            const shortNames = capitalize(`${fullName}`);

            const iconClass = emailVerified ? "bi bi-envelope-check" : "bi bi-envelope-exclamation";
            const iconColor = emailVerified ? "text-primary" : "text-secondary";
            const icon = `<i class="${iconClass} ${iconColor} me-2"></i>`;

            let html = '<div class="d-flex flex-column" style="max-width: 200px;">';
            html += `<h6 class="font-weight-bold text-gray-800 mb-0">${shortNames}</h6>`;
            html += '<span class="text-sm">';
            html += `
                    <a class="text-muted d-inline-block text-truncate" 
                       style="max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" 
                       href="mailto:${data}">
                       ${icon}${data}
                    </a>
                `;
            html += '</span>';
            html += '</div>';
            return html;
        }

    },
    {
        orderable: false,
        data: "person__document_number",
        width: "15%",
        className: DataTableFactory.classes.center,
        render: (data, type, row) => {
            return data ? data : "-";
        }
    },
    {
        orderable: false,
        data: "person__phone",
        width: "15%",
        className: DataTableFactory.classes.center,
        render: (data, type, row) => {
            return data ? data : "-";
        }
    },
    {
        orderable: false,
        data: "group_name",
        width: "15%",
        className: DataTableFactory.classes.center,
        render: function (data, type, row) {
            if (!data) return '';

            const translations = {
                'specialist': {label: 'Especialista', color: 'primary'},
                'administrator': {label: 'Administrador', color: 'primary'},
            };

            const groups = data.split(', ').map(g => translations[g] || {label: g, color: 'secondary'});

            return groups.map(g => `
                <span class="badge bg-transparent border border-${g.color}
                      text-truncate py-2 px-2 rounded-3 text-sm"
                      style="width: 100px; display: inline-block;"
                      data-bs-toggle="tooltip" 
                      title="${g.label}">
                    ${g.label}
                </span>
            `).join('');
        }
    },
    {
        orderable: false,
        data: "status",
        width: "15%",
        className: DataTableFactory.classes.center,
        render: (data, type, row) => {
            const {label, color} = statusChoices[data];
            return `
                <span class="badge bg-transparent border border-${color} border-1 text-${color} 
                    text-truncate py-2 px-2 rounded-3" 
                      style="width: 120px;"
                      data-bs-toggle="tooltip" 
                      data-bs-placement="top" 
                      title="${label}">
                    ${label}
                </span>
            `;
        }
    },
    {
        orderable: true,
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
        width: "5%",
        orderable: false,
        className: DataTableFactory.classes.center,
        render: (data, type, row) => {
            const statusMeta = {
                true: {icon: "bi bi-toggle-on"},
                false: {icon: "bi bi-toggle-off"},
            };

            const actions = Object.entries(tableActions);
            const menuItems = actions.map(([key, action]) => {
                const dangerClass = action.danger ? 'text-danger' : '';
                const isStatusAction = key === 'status';
                const icon = isStatusAction ? statusMeta[row.is_active].icon : action.icon;

                return `
                    <li>
                        <a class="dropdown-item ${key}-btn ${dangerClass}" href="#" data-id="${data}">
                            <i class="${icon} me-2"></i>${action.label}
                        </a>
                    </li>
                `;
            }).join('');

            return `
                <div class="dropdown">
                    <button class="btn btn-sm" type="button" data-bs-toggle="dropdown">
                        <i class="bi bi-three-dots-vertical"></i>
                    </button>
                    <ul class="dropdown-menu">
                        ${menuItems}
                    </ul>
                </div>
            `;
        }
    }
];