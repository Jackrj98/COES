import uuid

from crum import get_current_user
from django.db import models
from django.utils.translation import gettext_lazy as _


# ─────────────────────────────────────────
# Managers
# ─────────────────────────────────────────
class ActiveManager(models.Manager):
    """Returns only active objects."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class AuditModel(models.Model):
    """Abstract base model for all models."""

    class IsActiveChoices(models.IntegerChoices):
        DISABLED = 0, _("Disabled")
        ENABLED = 1, _("Enabled")

    class IsActiveColorChoices(models.IntegerChoices):
        DISABLED = 0, "secondary"
        ENABLED = 1, "success"

    class StatusChoices(models.IntegerChoices):
        ACTIVE = 1, _("Disable")
        INACTIVE = 0, _("Enable")

    external_id = models.UUIDField(
        _("External ID"), default=uuid.uuid4, unique=True, editable=False
    )
    is_active = models.BooleanField(
        _("Is active"),
        default=True,
        help_text=_("Check this box to enable the feature in the system."),
    )

    # audit data
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    deleted_at = models.DateTimeField(_("Deleted at"), null=True, blank=True)
    created_by = models.CharField(_("Created by"), max_length=255, null=True, blank=True)
    updated_by = models.CharField(_("Updated by"), max_length=255, null=True, blank=True)

    # Managers
    active = ActiveManager()
    objects = models.Manager()

    class Meta:
        abstract = True
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["is_active"]),
        ]

    @staticmethod
    def _get_user_identifier():
        user = get_current_user()
        if user and user.pk:
            return getattr(user, "email", None) or str(user)
        return "system"

    def save(self, *args, **kwargs):
        user_identifier = self._get_user_identifier()
        if not self.pk:
            self.created_by = user_identifier
        else:
            self.updated_by = user_identifier

        super().save(*args, **kwargs)

    def get_is_active_display(self):
        return self.IsActiveChoices(self.is_active).label

    def get_is_active_color_display(self):
        return self.IsActiveColorChoices(self.is_active).label
