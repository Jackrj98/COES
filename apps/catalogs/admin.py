from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from apps.catalogs.models import Catalog, CatalogItem
from apps.core.mixins import BaseAdminMixin


class CatalogCodeFilter(admin.SimpleListFilter):
    """Custom filter for catalog code prefix."""

    title = _("Code prefix")
    parameter_name = "code_prefix"

    def lookups(self, request, model_admin):
        return [
            ("cat", _("Catalog (cat_*)")),
            ("uni", _("Unit of measure (uni_*)")),
            ("other", _("Other codes")),
        ]

    def queryset(self, request, queryset):
        if self.value() == "cat":
            return queryset.filter(code__startswith="cat_")
        if self.value() == "uni":
            return queryset.filter(code__startswith="uni_")
        if self.value() == "other":
            return queryset.exclude(code__startswith="cat_").exclude(code__startswith="uni_")
        return queryset


@admin.register(Catalog)
class CatalogAdmin(BaseAdminMixin):
    """Admin configuration for the Catalog model."""

    ordering = ("-created_at", "-priority")
    search_fields = ("name", "code", "description", "external_id")
    list_filter = ("is_active", CatalogCodeFilter)

    list_display = (
        "external_id",
        "name",
        "code",
        "priority",
        "items_count",
        "is_active",
        "created_at",
    )

    fieldsets = (
        (_("Basic Information"), {"fields": ("name", "code", "description", "priority")}),
        (
            _("Status"),
            {
                "fields": ("is_active",),
            },
        ),
        (
            _("Audit Information"),
            {
                "fields": (
                    "external_id",
                    "created_at",
                    "updated_at",
                    "deleted_at",
                    "created_by",
                    "updated_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = (
        "external_id",
        "created_at",
        "updated_at",
        "deleted_at",
        "created_by",
        "updated_by",
    )

    def items_count(self, obj):
        """Display the number of items in the catalog."""
        count = obj.items.filter(is_active=True).count()
        url = f"/admin/catalogs/catalogitem/?catalog__id__exact={obj.id}"
        return mark_safe(f'<a href="{url}">{count}</a>')

    items_count.short_description = _("Items")
    items_count.admin_order_field = "items__count"


class CatalogItemCatalogFilter(admin.SimpleListFilter):
    """Custom filter for catalog items by catalog code."""

    title = _("Catalog")
    parameter_name = "catalog_code"

    def lookups(self, request, model_admin):
        catalogs = Catalog.objects.filter(is_active=True)[:20]
        return [(c.code, f"{c.name} ({c.code})") for c in catalogs]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(catalog__code=self.value())
        return queryset


@admin.register(CatalogItem)
class CatalogItemAdmin(BaseAdminMixin):
    """Admin configuration for CatalogItem model."""

    ordering = ("-created_at", "-priority")
    search_fields = ("name", "code", "description", "extra", "external_id")
    list_filter = ("is_active", "catalog", CatalogItemCatalogFilter)
    list_select_related = ("catalog",)

    list_display = (
        "external_id",
        "name",
        "code",
        "catalog_link",
        "priority",
        "extra",
        "is_active",
        "created_at",
    )

    fieldsets = (
        (_("Basic Information"), {"fields": ("name", "code", "description", "priority", "extra")}),
        (
            _("Catalog"),
            {
                "fields": ("catalog",),
            },
        ),
        (
            _("Status"),
            {
                "fields": ("is_active",),
            },
        ),
        (
            _("Audit Information"),
            {
                "fields": (
                    "external_id",
                    "created_at",
                    "updated_at",
                    "deleted_at",
                    "created_by",
                    "updated_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = (
        "external_id",
        "created_at",
        "updated_at",
        "deleted_at",
        "created_by",
        "updated_by",
    )
    raw_id_fields = ("catalog",)

    def catalog_link(self, obj):
        """Display catalog as a clickable link."""
        url = f"/admin/catalogs/catalog/{obj.catalog.id}/change/"
        return mark_safe(f'<a href="{url}">{obj.catalog.name} ({obj.catalog.code})</a>')

    catalog_link.short_description = _("Catalog")
    catalog_link.admin_order_field = "catalog__name"

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related("catalog")


# Inline admin for Catalog items within Catalog admin
class CatalogItemInline(admin.TabularInline):
    """Inline admin for Catalog items."""

    model = CatalogItem
    extra = 0
    fields = ("name", "code", "priority", "extra", "is_active")
    show_change_link = True
    classes = ("collapse",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("catalog")
