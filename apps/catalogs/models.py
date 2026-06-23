from django.core.exceptions import ValidationError
from django.core.validators import (
    MaxLengthValidator,
    MaxValueValidator,
    MinLengthValidator,
    MinValueValidator,
)
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.core.models import AuditModel


class Catalog(AuditModel):
    class CatalogCodes:
        SUPPLY_CATEGORY = "CAT_SUPPLY"
        UNIT_OF_MEASURE = "UNI_MEASURE"
        INBOUND_CONCEPT = "CONCEPT_IN"
        OUTBOUND_CONCEPT = "CONCEPT_OUT"

    name = models.CharField(
        _("Name"),
        max_length=255,
        unique=True,
        validators=[MaxLengthValidator(255), MinLengthValidator(3)],
    )
    code = models.SlugField(
        _("Code"),
        unique=True,
        max_length=50,
        validators=[MaxLengthValidator(50), MinLengthValidator(3)],
        help_text=_("Unique identifier code, only lower case, numbers and underscores"),
    )
    description = models.TextField(
        _("Description"), blank=True, null=True, validators=[MaxLengthValidator(1000)]
    )
    priority = models.PositiveIntegerField(
        _("Priority"),
        default=100,
        help_text=_("Priority level"),
        validators=[MinValueValidator(1), MaxValueValidator(100000)],
    )

    class Meta:
        db_table = "catalog"
        verbose_name = _("catalog")
        verbose_name_plural = _("catalogs")
        ordering = ["-created_at", "priority"]
        indexes = [models.Index(fields=["code"]), models.Index(fields=["is_active"])]
        permissions = (("view_catalogs", "Can view catalog list"),)

    def __str__(self):
        return self.code

    def get_absolute_url(self):
        return reverse("catalogs:catalogs:detail", kwargs={"external_id": self.external_id})


class CatalogItem(AuditModel):
    name = models.CharField(
        _("Name"),
        max_length=255,
        validators=[MaxLengthValidator(255), MinLengthValidator(3)],
    )
    code = models.SlugField(
        _("Code"),
        max_length=50,
        validators=[MaxLengthValidator(50), MinLengthValidator(3)],
        help_text=_("Unique identifier code, only lower case, numbers and underscores"),
    )
    description = models.CharField(
        _("Description"),
        max_length=255,
        blank=True,
        null=True,
        validators=[MaxLengthValidator(1000)],
    )
    priority = models.PositiveIntegerField(
        _("Priority"),
        default=100,
        validators=[MinValueValidator(1), MaxValueValidator(100000)],
    )
    extra = models.CharField(
        _("Extra value"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Auxiliary value, e.g. abbreviation 'ml' for 'Milliliter'"),
    )

    catalog = models.ForeignKey(
        "Catalog",
        on_delete=models.CASCADE,
        blank=False,
        null=False,
        related_name="items",
        verbose_name=_("Catalog"),
    )

    class Meta:
        db_table = "catalog_item"
        verbose_name = _("catalog item")
        verbose_name_plural = _("catalog items")
        ordering = ["-created_at", "priority"]
        unique_together = [("catalog", "code")]

    def __str__(self):
        return self.code

    def get_absolute_url(self):
        kwargs = {"catalog_reference": self.catalog.external_id, "external_id": self.external_id}
        return reverse("catalogs:items:detail", kwargs=kwargs)

    def clean(self):
        queryset = self.__class__.objects.filter(catalog=self.catalog, code=self.code).select_related("catalog")

        if self.pk:
            queryset = queryset.exclude(pk=self.pk)

        if queryset.exists():
            raise ValidationError(
                {"code": _("A catalog item with this code already exists in this catalog.")}
            )
