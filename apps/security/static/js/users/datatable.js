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

            return `
                <div class="d-flex align-items-center gap-3">
                    <div class="bg-secondary bg-opacity-25 rounded-3 d-flex align-items-center justify-content-center flex-shrink-0"
                         style="width: 40px; height: 40px;">
                        <span class="fw-bold fs-6">
                            ${fullName.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()}
                        </span>
                    </div>
                    <div>
                        <div class="fw-semibold">${fullName}</div>
                        <a href="mailto:${data}" class="text-muted small text-truncate d-block" style="max-width: 280px;">
                            ${data}
                        </a>
                    </div>
                </div>`;
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
        className: DataTableFactory.classes.center,
        render: function (data, type, row) {
            if (!data) return '';
            const translations = {
                'specialist': {label: 'Especialista', color: 'secondary'},
                'administrator': {label: 'Administrador', color: 'primary'},
            };
            const groups = data.split(', ').map(g => translations[g] || {label: g, color: 'secondary'});
            return groups.map(g => `
                <span class="badge bg-${g.color} bg-opacity-10 text-${g.color} rounded-pill py-2" style="width: 10em">
                    ${g.label}
                </span>`).join('');
        }
    },

    {
        orderable: false,
        data: "status", width: "13%", className: DataTableFactory.classes.center,
        render: (data) => {
            if (!data) return '<span class="text-muted">—</span>';
            const {color, label} = mapStatus[data] || {color: 'secondary', label: 'N/A'};
            return `
                <span class="badge bg-${color} bg-opacity-10 text-${color} rounded-pill py-2" style="width: 10em">
                    ${label}
                </span>`;
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