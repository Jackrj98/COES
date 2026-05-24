class DataTableFactory {
    static classes = {
        base: "align-middle py-2 px-2",
        center: "align-middle py-2 px-2 text-center",
        justify: "align-middle py-2 px-2 text-justify",
        end: "align-middle py-2 px-2 text-end",
    };

    constructor({
                    selector,
                    ajaxUrl,
                    columns,
                    order = [[0, "asc"]],
                    filters = [],
                    paginationClass = "pagination-primary",
                    rowClickAction = null,
                }) {
        this.selector = selector;
        this.ajaxUrl = ajaxUrl;
        this.columns = columns;
        this.order = order;
        this.filters = filters;
        this.paginationClass = paginationClass;
        this.rowClickAction = rowClickAction;
        this.table = null;
        this.timeout = null;
    }

    init() {
        this.table = $(this.selector).DataTable({
            ordering: true,
            processing: true,
            serverSide: true,
            colReorder: true,
            responsive: true,
            searching: false,
            autoWidth: true,
            ajax: {
                url: this.ajaxUrl,
                type: "GET",
                data: (d) => this.applyFilters(d),
            },
            order: this.order,
            columns: this.columns,
            dom: 'rt<"row mt-2"<"col-md-6 d-flex align-items-center"l><"col-md-6 d-flex justify-content-end align-items-center gap-3"ip>>',
            language: {
                url: "https://cdn.datatables.net/plug-ins/1.13.6/i18n/es-ES.json",
                lengthMenu: "Registros por página _MENU_",
                info: "_START_-_END_ de _TOTAL_",
                infoEmpty: "0-0 de 0",
                infoFiltered: "(filtrado de _MAX_ registros)",
                paginate: {
                    previous: "<i class='bi bi-chevron-left'></i>",
                    next: "<i class='bi bi-chevron-right'></i>"
                }
            },
            pagingType: "simple",
            drawCallback: (settings) => {
                this.initTooltips();
                this.setPaginationColor();
                if (this.rowClickAction) {
                    $(this.selector).find("tbody tr").off("click").on("click", (e) => {
                        const row = this.table.row(e.currentTarget);
                        if (row.data()) {
                            this.rowClickAction(row.data());
                        }
                    });
                }
            }
        });
        this.bindFilterEvents();
    }

    initTooltips() {
        if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
            const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
            tooltipTriggerList.forEach(el => new bootstrap.Tooltip(el));
        } else if (window.tabler && typeof window.tabler.init === 'function') {
            window.tabler.init();
        }
    }

    applyFilters(data) {
        this.filters.forEach(f => {
            const value = $(f.selector).val();
            if (f.type === "date-range" && value?.includes(" a ")) {
                const [from, to] = value.split(" a ").map(v => v.trim());
                data[`${f.field}_from`] = from;
                data[`${f.field}_to`] = to;
            } else {
                data[f.field] = value;
            }
        });
    }

    bindFilterEvents() {
        this.filters.forEach(f => {
            $(f.selector).on("change input", () => {
                clearTimeout(this.timeout);
                this.timeout = setTimeout(() => this.table.ajax.reload(), 300);
            });
        });

        const $clearFilters = $("#clear-filters");
        if ($clearFilters.length) {
            $clearFilters.on("click", () => {
                this.clearFilters();
                this.table.ajax.reload();
            });
        }
    }

    clearFilters() {
        this.filters.forEach(f => {
            const $element = $(f.selector);
            if ($element.hasClass('flatpickr-input')) {
                const flatpickrInstance = $element[0]._flatpickr;
                if (flatpickrInstance) {
                    flatpickrInstance.clear();
                } else {
                    $element.val('');
                }
            } else {
                $element.val('');
            }
        });
    }

    setPaginationColor() {
        document.querySelectorAll(`${this.selector} .dataTables_paginate .pagination`)
            .forEach(dt => dt.classList.add(this.paginationClass));
    }
}

function renderTruncatedTooltip(data, tooltip) {
    const safe = $('<div>').text(data).html();
    const title = (tooltip || data).replace(/"/g, '&quot;');
    return `
        <div class="d-flex flex-column">
            <span class="text-truncate d-inline-block" 
                  title="${title}" 
                  data-bs-toggle="tooltip" 
                  data-bs-placement="top">
                ${safe}
            </span>
        </div>
    `;
}

function renderDateTime(data) {
    const {date, time} = formatDateTime(data);
    return `
        <div class="d-flex flex-column">
            <p class="mb-0">${date}</p>
            <small class="text-sm text-muted">${time}</small>
        </div>
    `;
}

function createLinkRenderer(url, content, raw = false) {
    const safeContent = raw ? content : $('<div>').text(content).html();
    return `
        <a class="text-decoration-none text-secondary" href="${url}" type="button">
            ${safeContent}
        </a>
    `;
}