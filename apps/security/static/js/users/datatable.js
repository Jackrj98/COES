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
        width: "3%",
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
                <div class="d-flex flex-column" style="max-width: 22vw; min-width: 10vw;">
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
        className: DataTableFactory.classes.justify,
        render: (data, type, row) => {
            return data ? data : "-";
        }
    },
    {
        orderable: false,
        data: "person__phone",
        width: "12%",
        className: DataTableFactory.classes.justify,
        render: (data, type, row) => {
            return data ? data : "-";
        }
    },
    {
        orderable: false,
        data: "group_name",
        width: "14%",
        render: function (data, type, row) {
            if (!data) return '';
            const translations = {
                'specialist': {label: 'Especialista', color: 'secondary'},
                'administrator': {label: 'Administrador', color: 'secondary'},
            };
            const groups = data.split(', ').map(g => translations[g] || {label: g, color: 'secondary'});
            return groups.map(g => `
                <button type="button" class="btn btn-icon icon-left bg-${g.color} bg-opacity-25 rounded-pill px-2 py-1"
                        style="width: 120px; cursor: default;">
                    <span class="fw-semibold text-${g.color} text-truncate">${g.label}</span>
                </button>
            `).join('');
        }
    },
    {
        orderable: false,
        data: "status",
        width: "13%",
        render: (data, type, row) => {
            const {label, color} = mapStatus[data];
            return `
                <button type="button" class="btn btn-icon icon-left bg-${color} bg-opacity-25 rounded-pill px-2 py-1"
                        style="width: 120px; cursor: default;">
                    <span class="fw-semibold text-${color} text-truncate">${label}</span>
                </button>
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
        width: "10%",
        orderable: false,
        className: DataTableFactory.classes.center,
         render: (data, type, row) => {
            const detailUrl = `${urlPaginator}${data}/`;
            const editUrl = `${urlPaginator}${data}/update`;
            const statusUrl = `${urlPaginator}${data}/update-status/`;
            return `
                <div class="d-flex justify-content-center gap-1 flex-nowrap">
                    <button type="button" class="btn btn-icon btn-outline-secondary bg-opacity-25 rounded-circle border-0"
                            data-bs-toggle="tooltip" data-bs-placement="top" data-bs-trigger="hover"
                            title="Ver detalles"
                            onclick="window.location.href='${detailUrl}'">
                        <i class="bi bi-eye fs-6"></i>
                    </button>
                    <button type="button" class="btn btn-icon btn-outline-secondary bg-opacity-25 rounded-circle border-0"
                            data-bs-toggle="tooltip" data-bs-placement="top" data-bs-trigger="hover"
                            title="Editar detalles"
                            onclick="window.location.href='${editUrl}'">
                        <i class="bi bi-pencil-square fs-6"></i>
                    </button>
                    <button type="button"
                            class="btn btn-icon btn-outline-secondary bg-opacity-25 rounded-circle border-0 status-toggle-btn"
                            data-bs-toggle="tooltip" data-bs-placement="top" data-bs-trigger="hover"
                            title="${row.is_active ? 'Desactivar' : 'Activar'}"
                            data-url="${statusUrl}">
                        <i class="bi ${row.is_active ? 'bi-toggle-on' : 'bi-toggle-off'} fs-6"></i>
                    </button>
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