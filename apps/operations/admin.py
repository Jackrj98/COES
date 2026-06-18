from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.core.mixins import BaseAdminMixin
from apps.operations.models import Supplier


@admin.register(Supplier)
class SupplierAdmin(BaseAdminMixin):
    """Admin for a Supplier model."""

    ordering = ("-created_at",)
    search_fields = ("business_name", "email", "phone", "external_id")
    list_filter = ("is_active",)

    list_display = (
        "external_id",
        "business_name",
        "email",
        "phone",
        "delivery_days",
        "is_active",
    )

    fieldsets = (
        (_("Basic Information"), {"fields": ("business_name",)}),
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
