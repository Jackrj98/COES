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
            {selector: "#id_reason", field: "reason"},
            {selector: "#id_delivery_days", field: "delivery_days"},
        ],
        paginationClass: "pagination-primary"
    });
    table.init();
});


const columns = [
    {
        orderable: false,
        data: "business_name",
        width: "22%",
        className: DataTableFactory.classes.justify,
        render: (data, type, row) => {
            const detailUrl = `${urlPaginator}${row.external_id}/`;
            const initials = n => n.split(' ').slice(0, 2).map(w => w[0]).join('').toUpperCase();
            const colors = ['primary', 'success', 'danger', 'warning', 'info', 'secondary', 'dark'];
            const randomColor = colors[Math.floor(Math.random() * colors.length)];

            return `
                <div class="d-flex align-items-center gap-3">
                    <button type="button" class="btn btn-icon icon-left bg-primary bg-opacity-25 flex-shrink-0" 
                        style="width: 50px">
                        ${initials(data)}
                    </button>
                    <div class="text-start">
                        <a href="${detailUrl}" class="text-decoration-none text-reset fw-semibold">${data}</a>
                    </div>
                </div>
            `;
        }
    },
    {
        orderable: false,
        data: "reason",
        width: "20%",
        className: DataTableFactory.classes.justify,
        render: (data) => `<span class="text-muted">${data || '—'}</span>`
    },
    {
        orderable: false,
        data: "tax_id",
        width: "12%",
        className: DataTableFactory.classes.center,
        render: (data) => `<span class="fw-mono">${data || '—'}</span>`
    },
    {
        orderable: false,
        data: "delivery_days",
        width: "12%",
        className: DataTableFactory.classes.center,
        render: (data) => {
            let color = data <= 5 ? 'success' : (data <= 14 ? 'warning' : 'danger');
            return `
                <button type="button" class="btn btn-icon icon-left bg-${color} bg-opacity-25 rounded-pill px-3 py-1"
                        style="min-width: 70px; cursor: default;">
                    <span class="fw-semibold">${data} d</span>
                </button>
            `;
        }
    },
    {
        orderable: false,
        data: "email",
        width: "16%",
        className: DataTableFactory.classes.justify,
        render: (data) => `
            <div class="d-flex align-items-center justify-content-center gap-2">
                ${data || '—'}
            </div>
        `
    },
    {
        orderable: false,
        data: "phone",
        width: "12%",
        className: DataTableFactory.classes.center,
        render: (data) => `
            <div class="d-flex align-items-center justify-content-center gap-2">
                ${data || '—'}
            </div>
        `
    },
    {
        orderable: false,
        data: "is_active",
        width: "16%",
        className: DataTableFactory.classes.center,
        render: (data) => {
            const status = data ? 1 : 0;
            const label = statusChoices[status];
            const color = statusColorChoices[status];
            const icon = data ? 'bi-toggle-on' : 'bi-toggle-off';

            return `
                <button type="button" class="btn btn-icon icon-left bg-${color} bg-opacity-25 rounded-pill px-3 py-1"
                        style="min-width: 150px; cursor: default; width: 130px">
                    <span class="fw-semibold text-${color}">${label}</span>
                </button>
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
                    
                    <button type="button" class="btn btn-icon icon-left btn-outline-secondary bg-opacity-25 rounded-circle border-0" 
                            data-bs-toggle="tooltip" 
                            data-bs-placement="top" 
                            title="Editar detalles" 
                            onclick="window.location.href='${editUrl}'">
                        <i class="bi bi-pencil-square fs-6"></i>
                    </button>
                    
                     <button type="button" 
                            class="btn btn-icon icon-left btn-outline-secondary bg-opacity-25 rounded-circle border-0 status-toggle-btn" 
                            data-bs-toggle="tooltip" 
                            data-bs-placement="top" 
                            title="${row.is_active ? 'Desactivar proveedor' : 'Activar proveedor'}" 
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
                        console.error('Error:', error);
                        Swal.fire({
                            title: 'Error',
                            text: error.message,
                            timer: 3000,
                            timerProgressBar: true,
                            icon: 'error',
                            confirmButtonColor: '#4e73df',
                        }).then(() => window.location.reload());
                    });
            });
        });
});