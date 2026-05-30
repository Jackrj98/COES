from django.contrib import admin
from django.db.models import Count
from django.utils.translation import gettext_lazy as _

from apps.core.mixins import BaseAdminMixin

from .models import Batch, InventoryMovement, Supply


class BatchInline(admin.TabularInline):
    model = Batch
    extra = 0
    fields = ("number", "expiration_date", "stock", "purchase_unit_cost", "status")
    readonly_fields = ("stock",)
    show_change_link = True


class InventoryMovementInline(admin.TabularInline):
    model = InventoryMovement
    extra = 0
    fields = ("movement_type", "quantity", "concept", "previous_stock", "after_stock")
    readonly_fields = ("previous_stock", "after_stock")
    show_change_link = True


@admin.register(Supply)
class SupplyAdmin(BaseAdminMixin):
    list_display = ("name", "code", "category", "unit_of_measure", "batch_count")
    search_fields = ("name", "code", "description")
    list_filter = ("category",)
    inlines = [BatchInline]

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
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(batch_count=Count("batches"))

    @admin.display(description=_("Batches count"), ordering="batch_count")
    def batch_count(self, obj):
        return obj.batch_count


@admin.register(Batch)
class BatchAdmin(BaseAdminMixin):
    inlines = [InventoryMovementInline]
    list_display = ("number", "supply", "expiration_date", "stock", "status", "movement_count")
    list_filter = ("status", "expiration_date", "supply")
    search_fields = ("number", "supply__name")

    fieldsets = (
        (
            _("Batch Details"),
            {
                "fields": (
                    "supply",
                    "number",
                    "expiration_date",
                    "stock",
                    "purchase_unit_cost",
                    "status",
                    "purchase_order",
                )
            },
        ),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(movement_count=Count("movements", distinct=True))

    @admin.display(description=_("Movement count"), ordering="movement_count")
    def movement_count(self, obj):
        return obj.movement_count


@admin.register(InventoryMovement)
class InventoryMovementAdmin(BaseAdminMixin):
    list_display = (
        "batch",
        "movement_type",
        "quantity",
        "concept",
        "previous_stock",
        "after_stock",
    )
    list_filter = ("movement_type", "created_at")
    search_fields = ("batch__number", "concept")

    readonly_fields = ("previous_stock", "after_stock", "is_increment")

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
                    "previous_stock",
                    "after_stock",
                    "is_increment",
                )
            },
        ),
    )
