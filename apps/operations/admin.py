from django.contrib import admin
from django.db import models
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from apps.core.mixins import BaseAdminMixin
from apps.operations.models import (
    ExitDetail,
    ExitOrder,
    PurchaseOrder,
    PurchaseOrderDetail,
    Supplier,
)

# ==========================================
# FILTROS PERSONALIZADOS
# ==========================================


class PurchaseOrderStatusFilter(admin.SimpleListFilter):
    """Custom filter for purchase order status."""

    title = _("Status")
    parameter_name = "status"

    def lookups(self, request, model_admin):
        return PurchaseOrder.Status.choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


class ExitOrderStatusFilter(admin.SimpleListFilter):
    """Custom filter for exit order status."""

    title = _("Status")
    parameter_name = "status"

    def lookups(self, request, model_admin):
        return ExitOrder.Status.choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


# ==========================================
# INLINES
# ==========================================


class PurchaseOrderDetailInline(admin.TabularInline):
    """Inline for purchase order details."""

    model = PurchaseOrderDetail
    extra = 0
    fields = [
        "supply",
        "quantity_requested",
        "quantity_received",
        "unit_cost",
        "line_total_display",
    ]
    readonly_fields = ["line_total_display"]

    def line_total_display(self, obj):
        if obj.pk:
            return f"${obj.line_total:,.2f}"
        return "-"

    line_total_display.short_description = _("Line Total")


class ExitDetailInline(admin.TabularInline):
    """Inline for exit order details."""

    model = ExitDetail
    extra = 0
    fields = [
        "supply",
        "batch",
        "quantity_requested",
        "quantity_dispatched",
        "unit_cost",
        "line_total_display",
    ]
    readonly_fields = ["line_total_display"]

    def line_total_display(self, obj):
        if obj.pk:
            return f"${obj.line_total:,.2f}"
        return "-"

    line_total_display.short_description = _("Line Total")


@admin.register(Supplier)
class SupplierAdmin(BaseAdminMixin):
    """Admin for a Supplier model."""

    ordering = ("-created_at",)
    search_fields = ("business_name", "contact_name", "tax_id", "email", "phone", "external_id")
    list_filter = ("is_active",)

    list_display = (
        "external_id",
        "business_name",
        "contact_name",
        "tax_id",
        "email",
        "phone",
        "delivery_days",
        "is_active",
    )

    fieldsets = (
        (_("Basic Information"), {"fields": ("business_name", "contact_name", "tax_id")}),
        (_("Contact Information"), {"fields": ("email", "phone", "address")}),
        (_("Business Information"), {"fields": ("delivery_days",)}),
        (
            _("Audit"),
            {
                "fields": (
                    "is_active",
                    "external_id",
                    "created_at",
                    "updated_at",
                    "created_by",
                    "updated_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = ("external_id", "created_at", "updated_at", "created_by", "updated_by")


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(BaseAdminMixin):
    """Admin for PurchaseOrder model."""

    ordering = ("-created_at",)
    search_fields = ("order_number", "supplier__business_name", "external_id")
    list_filter = (PurchaseOrderStatusFilter, "is_active")
    inlines = [PurchaseOrderDetailInline]

    list_display = (
        "external_id",
        "order_number",
        "supplier_name",
        "status_colored",
        "total_items",
        "total_amount",
        "created_at",
        "is_active",
    )

    list_select_related = ("supplier",)

    fieldsets = (
        (_("Order Information"), {"fields": ("order_number", "supplier", "status")}),
        (_("Delivery Information"), {"fields": ("estimated_delivery", "actual_delivery")}),
        (_("Additional Information"), {"fields": ("observations", "motive")}),
        (
            _("Audit"),
            {
                "fields": (
                    "is_active",
                    "external_id",
                    "created_at",
                    "updated_at",
                    "created_by",
                    "updated_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = (
        "order_number",
        "external_id",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    )

    def supplier_name(self, obj):
        return obj.supplier.business_name

    supplier_name.short_description = _("Supplier")
    supplier_name.admin_order_field = "supplier__business_name"

    def status_colored(self, obj):
        colors = {
            PurchaseOrder.Status.DRAFT: "gray",
            PurchaseOrder.Status.SENT: "orange",
            PurchaseOrder.Status.COMPLETED: "green",
            PurchaseOrder.Status.CANCELLED: "red",
        }
        color = colors.get(obj.status, "black")
        return mark_safe(
            f'<span style="color: {color}; font-weight: bold;">{obj.get_status_display()}</span>'
        )

    status_colored.short_description = _("Status")
    status_colored.admin_order_field = "status"

    def total_items(self, obj):
        return obj.details.aggregate(total=models.Sum("quantity_requested"))["total"] or 0

    total_items.short_description = _("Total Items")

    def total_amount(self, obj):
        total = (
            obj.details.aggregate(
                total=models.Sum(models.F("quantity_received") * models.F("unit_cost"))
            )["total"]
            or 0
        )
        return f"${total:,.2f}"

    total_amount.short_description = _("Total Amount")


@admin.register(PurchaseOrderDetail)
class PurchaseOrderDetailAdmin(BaseAdminMixin):
    """Admin for PurchaseOrderDetail model."""

    ordering = ("-created_at",)
    search_fields = ("order__order_number", "supply__name", "external_id")
    list_filter = ("is_active",)

    list_display = (
        "external_id",
        "order_number",
        "supply_name",
        "quantity_requested",
        "quantity_received",
        "unit_cost",
        "line_total_display",
        "is_active",
    )

    list_select_related = ("order", "supply")

    def order_number(self, obj):
        return obj.order.order_number

    order_number.short_description = _("Order Number")
    order_number.admin_order_field = "order__order_number"

    def supply_name(self, obj):
        return obj.supply.name

    supply_name.short_description = _("Supply")
    supply_name.admin_order_field = "supply__name"

    def line_total_display(self, obj):
        return f"${obj.line_total:,.2f}"

    line_total_display.short_description = _("Line Total")


# ==========================================
# EXIT ORDER ADMIN
# ==========================================


@admin.register(ExitOrder)
class ExitOrderAdmin(BaseAdminMixin):
    """Admin for ExitOrder model."""

    ordering = ("-created_at",)
    search_fields = ("order_number", "requested_by", "external_id", "observations", "motive")
    list_filter = (ExitOrderStatusFilter, "is_active", "created_at")
    inlines = [ExitDetailInline]

    list_display = (
        "external_id",
        "order_number",
        "requested_by",
        "status_colored",
        "total_items",
        "total_amount",
        "items_dispatched",
        "created_at",
        "is_active",
    )

    fieldsets = (
        (_("Order Information"), {"fields": ("order_number", "status", "requested_by")}),
        (_("Financial Information"), {"fields": ("subtotal", "total"), "classes": ("collapse",)}),
        (_("Additional Information"), {"fields": ("observations", "motive")}),
        (
            _("Audit"),
            {
                "fields": (
                    "is_active",
                    "external_id",
                    "created_at",
                    "updated_at",
                    "created_by",
                    "updated_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = (
        "order_number",
        "subtotal",
        "total",
        "external_id",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    )

    def status_colored(self, obj):
        """Display status with color coding."""
        colors = {
            ExitOrder.Status.DRAFT: "gray",
            ExitOrder.Status.COMPLETED: "green",
            ExitOrder.Status.CANCELLED: "red",
        }
        color = colors.get(obj.status, "black")
        return mark_safe(
            f'<span style="color: {color}; font-weight: bold;">{obj.get_status_display()}</span>'
        )

    status_colored.short_description = _("Status")
    status_colored.admin_order_field = "status"

    def total_items(self, obj):
        """Total number of unique items in the order."""
        return obj.details.count()

    total_items.short_description = _("Total Items")

    def total_amount(self, obj):
        """Display formatted total amount."""
        return f"${obj.total:,.2f}"

    total_amount.short_description = _("Total Amount")

    def items_dispatched(self, obj):
        """Total quantity dispatched across all details."""
        total = obj.details.aggregate(total=models.Sum("quantity_dispatched"))["total"] or 0
        return f"{total} units"

    items_dispatched.short_description = _("Items Dispatched")

    def get_queryset(self, request):
        """Optimize queryset with prefetch_related."""
        return super().get_queryset(request).prefetch_related("details")

    def save_model(self, request, obj, form, change):
        """Save model and update totals."""
        if not change:
            obj.requested_by = (
                obj.requested_by or request.user.get_full_name() or request.user.email
            )
        super().save_model(request, obj, form, change)
        obj.recalculate_totals()
        obj.save(update_fields=["subtotal", "total"])

    def get_readonly_fields(self, request, obj=None):
        """Make fields readonly if the order is completed or cancelled."""
        readonly = super().get_readonly_fields(request, obj)
        if obj and obj.status in [ExitOrder.Status.COMPLETED, ExitOrder.Status.CANCELLED]:
            return readonly + ("status", "requested_by", "observations", "motive")
        return readonly

    actions = ["mark_as_completed", "mark_as_cancelled"]

    def mark_as_completed(self, request, queryset):
        """Mark selected orders as completed."""
        updated = queryset.update(status=ExitOrder.Status.COMPLETED)
        self.message_user(request, _(f"{updated} orders marked as completed."))

    mark_as_completed.short_description = _("Mark selected orders as completed")

    def mark_as_cancelled(self, request, queryset):
        """Mark selected orders as canceled."""
        updated = queryset.update(status=ExitOrder.Status.CANCELLED)
        self.message_user(request, _(f"{updated} orders marked as cancelled."))

    mark_as_cancelled.short_description = _("Mark selected orders as cancelled")


@admin.register(ExitDetail)
class ExitDetailAdmin(BaseAdminMixin):
    """Admin for ExitDetail model."""

    ordering = ("-created_at",)
    search_fields = (
        "exit_order__order_number",
        "supply__name",
        "supply__code",
        "batch__batch_number",
        "external_id",
    )
    list_filter = ("is_active", "created_at")

    list_display = (
        "external_id",
        "order_number",
        "supply_name",
        "batch_number",
        "quantity_requested",
        "quantity_dispatched",
        "unit_cost",
        "line_total_display",
        "pending_quantity",
        "dispatch_percentage_bar",
        "is_active",
    )

    list_select_related = ("exit_order", "supply", "batch")

    def order_number(self, obj):
        return obj.exit_order.order_number

    order_number.short_description = _("Order Number")
    order_number.admin_order_field = "exit_order__order_number"

    def supply_name(self, obj):
        return obj.supply.name

    supply_name.short_description = _("Supply")
    supply_name.admin_order_field = "supply__name"

    def batch_number(self, obj):
        if obj.batch:
            return obj.batch.batch_number
        return "-"

    batch_number.short_description = _("Batch Number")
    batch_number.admin_order_field = "batch__batch_number"

    def line_total_display(self, obj):
        return f"${obj.line_total:,.2f}"

    line_total_display.short_description = _("Line Total")

    def pending_quantity(self, obj):
        pending = obj.quantity_requested - obj.quantity_dispatched
        if pending > 0:
            return mark_safe(f'<span style="color: orange;">{pending}</span>')
        return f"{pending}"

    pending_quantity.short_description = _("Pending")

    def dispatch_percentage_bar(self, obj):
        """Display dispatch progress as a percentage bar."""
        if obj.quantity_requested == 0:
            percentage = 0
        else:
            percentage = (obj.quantity_dispatched / obj.quantity_requested) * 100

        # Determine color based on percentage
        if percentage >= 100:
            color = "green"
        elif percentage >= 50:
            color = "orange"
        else:
            color = "red"

        return mark_safe(f"""
            <div style="background-color: #f0f0f0; border-radius: 4px; overflow: hidden; width: 100px;">
                <div style="background-color: {color}; width: {percentage}%; height: 20px; text-align: center; color: white; font-size: 11px; line-height: 20px;">
                    {percentage:.0f}%
                </div>
            </div>
        """)

    dispatch_percentage_bar.short_description = _("Dispatch Progress")

    def get_readonly_fields(self, request, obj=None):
        """Make fields readonly if order is completed or cancelled."""
        readonly = super().get_readonly_fields(request, obj)
        if (
            obj
            and obj.exit_order
            and obj.exit_order.status in [ExitOrder.Status.COMPLETED, ExitOrder.Status.CANCELLED]
        ):
            return readonly + ("quantity_dispatched", "unit_cost", "batch")
        return readonly

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of details from completed/cancelled orders."""
        if (
            obj
            and obj.exit_order
            and obj.exit_order.status in [ExitOrder.Status.COMPLETED, ExitOrder.Status.CANCELLED]
        ):
            return False
        return super().has_delete_permission(request, obj)
