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
            {selector: "#id_search", field: "search"},
            {selector: "#id_group", field: "group"}
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
        width: "4%",
        className: DataTableFactory.classes.center,
        render: (data, type, row, meta) => {
            return meta.settings._iDisplayStart + meta.row + 1;
        }
    },
    {
        orderable: false,
        data: "email",
        width: "22%",
        className: DataTableFactory.classes.justify,
        render: (data, type, row) => {
            const {person__last_name: lastName, person__first_name: firstName, email_verified: emailVerified} = row;
            const fullName = lastName ? `${firstName} ${lastName}`.trim() : "-";
            const iconClass = emailVerified ? "bi bi-envelope-check" : "bi bi-envelope-exclamation";
            const iconColor = emailVerified ? "text-primary" : "text-secondary";

            return `
                <div class="d-flex flex-column" style="max-width: 22vw; min-width: 0;">
                    <h6 class="fw-semibold mb-0 text-truncate">${capitalize(fullName)}</h6>
                    <a class="text-muted text-truncate text-sm d-block" 
                       href="mailto:${data}" 
                       title="${data}"
                       style="max-width: 100%;">
                        <i class="${iconClass} ${iconColor} me-1"></i>${data}
                    </a>
                </div>
            `;
        }
    },
    {
        orderable: false,
        data: "person__document_number",
        width: "12%",
        className: DataTableFactory.classes.center,
        render: (data, type, row) => {
            return data ? data : "-";
        }
    },
    {
        orderable: false,
        data: "person__phone",
        width: "12%",
        className: DataTableFactory.classes.center,
        render: (data, type, row) => {
            return data ? data : "-";
        }
    },
    {
        orderable: false,
        data: "group_name",
        width: "16%",
        className: DataTableFactory.classes.center,
        render: function (data, type, row) {
            if (!data) return '';

            const translations = {
                'specialist': {label: 'Especialista', color: 'secondary'},
                'administrator': {label: 'Administrador', color: 'secondary'},
            };

            const groups = data.split(', ').map(g => translations[g] || {label: g, color: 'secondary'});
            return groups.map(g => `
                <span class="badge bg-${g.color}-subtle text-${g.color}-emphasis border border-${g.color}-subtle text-truncate py-2 px-2 rounded-3"
                      style="max-width: 16vw; min-width: 0; width: 120px;"
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
        width: "12%",
        className: DataTableFactory.classes.center,
        render: (data, type, row) => {
            const {label, color} = mapStatus[data];
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
        width: "18%",
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
            const statusMeta = {
                true: {icon: "bi bi-toggle-on"},
                false: {icon: "bi bi-toggle-off"},
            };

            const actions = Object.entries(tableActions);
            const menuItems = actions.map(([key, action]) => {
                const dangerClass = action.danger ? 'text-danger' : '';
                const isStatusAction = key === 'status';
                const icon = isStatusAction ? statusMeta[row.is_active].icon : action.icon;

                let actionUrl = action.url;
                const uuidPattern = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
                if (uuidPattern.test(actionUrl)) {
                    actionUrl = actionUrl.replace(uuidPattern, data);
                }
                if (isStatusAction) {
                    const status = row.is_active ? 0 : 1;
                    return `
                        <li>
                            <a class="dropdown-item status-toggle-btn ${dangerClass}" 
                               href="javascript:void(0)" 
                               data-id="${data}"
                               data-url="${actionUrl}">
                                <i class="${icon} me-2"></i>${action.label}
                            </a>
                        </li>
                    `;
                }

                return `
                    <li>
                        <a class="dropdown-item ${key}-btn ${dangerClass}" 
                           href="${actionUrl}" 
                           data-id="${data}">
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

document.addEventListener('click', function (e) {
    const btn = e.target.closest('.status-toggle-btn');
    if (!btn) return;
    e.preventDefault();

    const url = btn.dataset.url;

    fetch(url, {
        headers: {'X-Requested-With': 'XMLHttpRequest'}
    })
        .then(r => r.json())
        .then(data => {
            if (!data.success) {
                return window.location.reload();
            }

            Swal.fire({
                title: data.title,
                html: `<p class="text-muted mb-1">${data.description}</p>
                   <small class="text-muted">${data.email}</small><br>
                `,
                icon: 'question',
                showCancelButton: true,
                confirmButtonText: 'Confirmar',
                cancelButtonText: 'Cancelar',
                buttonsStyling: false,
                customClass: {
                    confirmButton: 'btn btn-primary me-3',
                    cancelButton: 'btn btn-outline-secondary'
                }
            }).then(result => {
                if (!result.isConfirmed) return;
                fetch(url, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                })
                    .then(r => r.json())
                    .then(response => {
                        Swal.fire({
                            title: 'Information',
                            text: response.message,
                            icon: 'success',
                            timer: 3000,
                            timerProgressBar: true,
                            confirmButtonColor: '#4e73df',
                            backdrop: false,
                            allowOutsideClick: false,
                            allowEscapeKey: false,
                        }).then(() => window.location.reload());
                    })
                    .catch((error) => {
                        Swal.fire({
                            title: 'Error',
                            text: error.message,
                            icon: 'error',
                            timer: 3000,
                            timerProgressBar: true,
                            confirmButtonColor: '#4e73df',
                        }).then(() => window.location.reload());
                    });
            });
        });
});