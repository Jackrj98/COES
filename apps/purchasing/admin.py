from django.contrib import admin
from django.db import models
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from apps.core.mixins import BaseAdminMixin
from apps.purchasing.models import OrderDetail, PurchaseOrder, Supplier


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


@admin.register(Supplier)
class SupplierAdmin(BaseAdminMixin):
    ordering = ("-created_at",)
    search_fields = ("business_name", "reason", "tax_id", "email", "phone", "external_id")
    list_filter = ("is_active",)

    list_display = (
        "external_id",
        "business_name",
        "reason",
        "tax_id",
        "email",
        "phone",
        "delivery_days",
        "is_active",
    )


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(BaseAdminMixin):
    ordering = ("-created_at",)
    search_fields = ("order_number", "supplier__business_name", "external_id")
    list_filter = (PurchaseOrderStatusFilter, "is_active")

    list_display = (
        "external_id",
        "order_number",
        "supplier_name",
        "status_colored",
        "total_items",
        "created_at",
        "is_active",
    )

    list_select_related = ("supplier",)

    def supplier_name(self, obj):
        return obj.supplier.business_name

    supplier_name.short_description = _("Supplier")
    supplier_name.admin_order_field = "supplier__business_name"

    def status_colored(self, obj):
        colors = {
            0: "gray",  # Draft
            1: "orange",  # Sent
            2: "green",  # Completed
            3: "red",  # Cancelled
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


@admin.register(OrderDetail)
class OrderDetailAdmin(BaseAdminMixin):
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
