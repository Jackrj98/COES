from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.catalogs.models import Catalog
from apps.core.models import AuditModel
from apps.core.utils.helpers import generate_upload_path


class Supply(AuditModel):
    """Represents a supply item in the system."""

    name = models.CharField(_("Name"), max_length=255)
    code = models.CharField(
        _("Code"),
        max_length=50,
        unique=True,
        help_text=_("Unique identifier code, numbers and underscores"),
    )
    description = models.CharField(_("Description"), max_length=255)
    image_url = models.ImageField(
        _("Image URL"), upload_to=generate_upload_path, blank=True, null=True
    )
    stock_min = models.PositiveIntegerField(
        _("Stock min"), default=10, help_text=_("Notify me when stock reaches this level")
    )

    category = models.ForeignKey(
        "catalogs.CatalogItem",
        on_delete=models.PROTECT,
        related_name="supplies_by_category",
        verbose_name=_("Category"),
        limit_choices_to={"catalog__code": Catalog.CatalogCodes.SUPPLY_CATEGORY},
        null=True,
        blank=True,
    )

    unit_of_measure = models.ForeignKey(
        "catalogs.CatalogItem",
        on_delete=models.PROTECT,
        related_name="supplies_by_unit",
        verbose_name=_("Unit of Measure"),
        limit_choices_to={"catalog__code": Catalog.CatalogCodes.UNIT_OF_MEASURE},
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "supply"
        verbose_name = _("Supply")
        verbose_name_plural = _("Supplies")
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["code"]), models.Index(fields=["name"])]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def get_absolute_url(self):
        return reverse("inventory:supplies:detail", kwargs={"external_id": self.external_id})

    @property
    def initials(self):
        name_parts = self.name.split()
        initials = "".join(part[0] for part in name_parts[:2])
        return initials.upper()

    @property
    def stock_available(self):
        return self.batches.aggregate(models.Sum("stock"))["stock__sum"] or 0

    def get_image(self):
        """Get the URL of the user's image."""
        if self.image_url:
            return f"{settings.MEDIA_URL}{self.image_url.url}"
        return None

    @property
    def expiring_soon(self):
        today = timezone.now().date()
        threshold = today + timedelta(days=30)
        return self.batches.filter(expiry_date__gte=today, expiry_date__lte=threshold).count()


class Batch(AuditModel):
    """Represents a batch of supplies, defining its properties, state, and related information."""

    class BatchStatus(models.IntegerChoices):
        DISCARDED = 0, _("Discarded")
        ACTIVE = 1, _("Active")
        EXPIRED = 2, _("Expired")
        DEPLETED = 3, _("Depleted")

        @property
        def style(self):
            configs = {
                self.DISCARDED.value: {"color": "secondary"},
                self.ACTIVE.value: {"color": "success"},
                self.EXPIRED.value: {"color": "danger"},
                self.DEPLETED.value: {"color": "warning"},
            }
            return configs[self.value]

        @property
        def color(self) -> str:
            return self.style["color"]

        @classmethod
        def get_ui_map(cls):
            return {item.value: {"color": item.color, "label": item.label} for item in cls}

    # Fields
    batch_number = models.CharField(_("Batch Number"), max_length=100)
    expiry_date = models.DateField(_("Expiry date"))
    initial_quantity = models.PositiveIntegerField(_("Initial quantity"), default=0)
    current_quantity = models.PositiveIntegerField(_("Current quantity"), default=0)
    unit_cost = models.DecimalField(_("Unit cost"), max_digits=12, decimal_places=2)
    status = models.PositiveIntegerField(
        _("Status"), choices=BatchStatus, default=BatchStatus.ACTIVE
    )
    # Relationships
    supply = models.ForeignKey(
        "Supply", on_delete=models.PROTECT, related_name="batches", verbose_name=_("Supply")
    )

    class Meta:
        db_table = "batch"
        verbose_name = _("Batch")
        verbose_name_plural = _("Batches")
        ordering = ["-expiry_date"]
        unique_together = (("supply", "batch_number"),)

    def __str__(self):
        return f"{self.batch_number} ({self.supply.name})"

    def get_absolute_url(self):
        kwargs = {"supply_reference": self.supply.external_id, "external_id": self.external_id}
        return reverse("inventory:batches:detail", kwargs=kwargs)

    def clean(self):
        queryset = self.__class__.objects.filter(supply=self.supply, batch_number=self.batch_number)

        if self.pk:
            queryset = queryset.exclude(pk=self.pk)

        if queryset.exists():
            raise ValidationError(
                {"batch_number": _("A batch with this number already exists for this supply.")}
            )

    @property
    def is_expired(self):
        return self.expiry_date < timezone.now().date()

    @property
    def days_until_expiry(self):
        if not self.expiry_date:
            return None

        delta = self.expiry_date - timezone.now().date()
        return delta.days

    @property
    def batch_total_cost(self):
        return round(self.current_quantity * self.unit_cost, 2)
