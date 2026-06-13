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
        data: "external_id",
        width: "3%",
        className: DataTableFactory.classes.center,
        render: (data, type, row, meta) => {
            return meta.settings._iDisplayStart + meta.row + 1;
        }
    },
    {
        orderable: false,
        data: "first_name",
        width: "18%",
        className: DataTableFactory.classes.justify,
        render: (data, type, row) => {
            const {external_id, business_name: business} = row;
            const detailUrl = `${urlPaginator}${external_id}/`;
            const initials = n => n.split(' ').slice(0, 2).map(w => w[0]).join('').toUpperCase();

            return `
                <div class="d-flex align-items-center gap-3"
                     data-bs-toggle="tooltip"
                     data-bs-placement="top"
                     data-bs-original-title="${business}">
                    <div class="bg-secondary bg-opacity-25 rounded-3 d-flex align-items-center justify-content-center flex-shrink-0"
                         style="width: 40px; height: 40px;">
                        <span class="font-bold fs-6 text-secondary">${initials(business)}</span>
                    </div>
                    <a href="${detailUrl}" class="text-decoration-none text-reset d-block">
                        <div class="text-start">
                            <div class="font-bold">${data} ${row.last_name}</div>
                            <div class="small text-muted text-uppercase" style="font-size: 0.75rem; letter-spacing: 0.05em;">
                                ${business}
                            </div>
                        </div>
                    </a>
                </div>`;
        }
    },
    {
        orderable: false,
        data: "document_number",
        width: "12%",
        className: DataTableFactory.classes.center,
        render: (data) => `<span class="fw-mono">${data || '—'}</span>`
    },
    {
        orderable: false,
        data: "delivery_days",
        width: "2%",
        className: DataTableFactory.classes.center,
        render: (data) => {
            let color = data <= 5 ? 'success' : (data <= 14 ? 'warning' : 'danger');
            return `
                <span class="badge bg-${color} bg-opacity-10 text-${color} rounded-pill py-2" style="width: 4em">
                    ${data}
                </span>`;
        }
    },
    {
        orderable: false,
        data: "email",
        width: "20%",
        className: DataTableFactory.classes.justify,
        render: (data) => {
            return `
                    <div class="d-flex flex-column"  style="max-width: 15vw; min-width: 0;">
                        <span class="fw-semibold mb-0 text-truncate d-block" data-bs-toggle="tooltip" title="${data || '-'}">
                            ${data || '?'}
                        </span>
                    </div>
                `;
        }
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
        width: "14%",
        className: DataTableFactory.classes.center,
        render: (data) => {
            const status = data ? 1 : 0;
            const label = statusChoices[status];
            const color = statusColorChoices[status];
            return `
                <span class="badge bg-${color} bg-opacity-10 text-${color} rounded-pill py-2" style="width: 10vw">
                    ${label}
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