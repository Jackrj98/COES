from django.contrib import admin
from django.db.models import Count, Sum
from django.utils.translation import gettext_lazy as _

from apps.core.mixins import BaseAdminMixin

from .models import Batch, InventoryMovement, Supply


class BatchInline(admin.TabularInline):
    model = Batch
    extra = 0
    fields = (
        "batch_number",
        "expiry_date",
        "current_quantity",
        "unit_cost",
        "status",
    )
    readonly_fields = ("current_quantity",)
    show_change_link = True
    can_delete = False


class InventoryMovementInline(admin.TabularInline):
    model = InventoryMovement
    extra = 0
    fields = ("movement_type", "quantity", "concept", "previous_stock", "after_stock", "status")
    readonly_fields = ("previous_stock", "after_stock", "is_increment", "unit_cost_at_movement")
    show_change_link = True
    can_delete = False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("batch")


@admin.register(Supply)
class SupplyAdmin(BaseAdminMixin):
    list_display = (
        "name",
        "code",
        "category",
        "unit_of_measure",
        "stock_available",
        "stock_min",
        "batch_count",
    )
    search_fields = ("name", "code", "description")
    list_filter = ("category", "unit_of_measure", "is_active")
    list_editable = ("stock_min",)
    inlines = [BatchInline]
    readonly_fields = ("stock_available",)

    fieldsets = (
        (
            _("General Information"),
            {
                "fields": (
                    "name",
                    "code",
                    "description",
                    "image_url",
                    "stock_min",
                    "category",
                    "unit_of_measure",
                )
            },
        ),
        (
            _("Audit Information"),
            {
                "fields": (
                    "is_active",
                    "created_at",
                    "updated_at",
                    "created_by",
                    "updated_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            batch_count=Count("batches", distinct=True),
            total_stock=Sum("batches__current_quantity"),
        )

    @admin.display(description=_("Available stock"), ordering="total_stock")
    def stock_available(self, obj):
        if hasattr(obj, "total_stock") and obj.total_stock is not None:
            return obj.total_stock
        return obj.stock_available

    @admin.display(description=_("Batches count"), ordering="batch_count")
    def batch_count(self, obj):
        return obj.batch_count

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user.email
        obj.updated_by = request.user.email
        super().save_model(request, obj, form, change)


@admin.register(Batch)
class BatchAdmin(BaseAdminMixin):
    inlines = [InventoryMovementInline]
    list_display = (
        "batch_number",
        "supply",
        "expiry_date",
        "current_quantity",
        "initial_quantity",
        "status",
        "is_expired",
        "days_until_expiry",
        "movement_count",
    )
    list_filter = ("status", "expiry_date", "supply")
    search_fields = ("batch_number", "supply__name", "supply__code")
    readonly_fields = ("current_quantity", "is_expired", "days_until_expiry", "batch_total_cost")
    list_editable = ("status",)

    fieldsets = (
        (
            _("Batch Details"),
            {
                "fields": (
                    "supply",
                    "batch_number",
                    "expiry_date",
                    "initial_quantity",
                    "current_quantity",
                    "unit_cost",
                    "status",
                )
            },
        ),
        (
            _("Calculated Information"),
            {
                "fields": (
                    "is_expired",
                    "days_until_expiry",
                    "batch_total_cost",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            _("Audit Information"),
            {
                "fields": (
                    "is_active",
                    "created_at",
                    "updated_at",
                    "created_by",
                    "updated_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(movement_count=Count("movements", distinct=True)).select_related(
            "supply"
        )

    @admin.display(description=_("Movement count"), ordering="movement_count")
    def movement_count(self, obj):
        return obj.movement_count

    @admin.display(description=_("Expired"), boolean=True)
    def is_expired(self, obj):
        return obj.is_expired

    @admin.display(description=_("Days until expiry"))
    def days_until_expiry(self, obj):
        days = obj.days_until_expiry
        if days is not None:
            if days < 0:
                return _("Expired")
            return f"{days} days"
        return "-"

    @admin.display(description=_("Total cost"))
    def batch_total_cost(self, obj):
        return f"${obj.batch_total_cost:,.2f}"

    def save_model(self, request, obj, form, change):
        if not change:
            obj.initial_quantity = obj.current_quantity
        super().save_model(request, obj, form, change)


@admin.register(InventoryMovement)
class InventoryMovementAdmin(BaseAdminMixin):
    list_display = (
        "id",
        "batch",
        "movement_type",
        "quantity",
        "concept",
        "previous_stock",
        "after_stock",
        "status",
        "created_at",
    )
    list_filter = ("movement_type", "status", "created_at", "is_increment")
    search_fields = ("batch__batch_number", "concept", "observation")
    readonly_fields = (
        "previous_stock",
        "after_stock",
        "is_increment",
        "unit_cost_at_movement",
        "created_at",
        "updated_at",
    )
    list_select_related = ("batch", "batch__supply")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    fieldsets = (
        (
            _("Movement Details"),
            {
                "fields": (
                    "batch",
                    "movement_type",
                    "concept",
                    "quantity",
                    "observation",
                    "status",
                )
            },
        ),
        (
            _("Stock Tracking"),
            {
                "fields": (
                    "previous_stock",
                    "after_stock",
                    "is_increment",
                    "unit_cost_at_movement",
                )
            },
        ),
        (
            _("Source Documents"),
            {
                "fields": (
                    "purchase_order",
                    "exit_order",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            _("Audit Information"),
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "created_by",
                    "updated_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("batch", "batch__supply", "purchase_order", "exit_order")
        )

    @admin.display(description=_("Movement"), ordering="movement_type")
    def movement_with_icon(self, obj):
        icon = obj.get_movement_type_display()
        if hasattr(obj.movement_type, "icon"):
            icon = f'<i class="{obj.movement_type.icon}"></i> {icon}'
        return icon

    movement_with_icon.allow_tags = True
