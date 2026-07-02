import secrets
from datetime import timedelta

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _

from apps.core.models import AuditModel
from apps.security.management.management import UserManager
from apps.security.utils.validators import django_id_validator, text_only

# ─────────────────────────────────────────
# Notification Model
# ─────────────────────────────────────────


class Notification(AuditModel):

    class TypeChoices(models.IntegerChoices):
        ALERT = 1, _("Alert")
        NOTIFICATION = 2, _("Notification")

    subject = models.CharField(_("Subject"), max_length=255)
    type = models.IntegerField(
        _("Type"), choices=TypeChoices, default=TypeChoices.NOTIFICATION
    )
    message = models.TextField(_("Message"))

    #  External channels
    reference_url = models.URLField(_("Reference URL"), blank=True, null=True)
    send_email = models.BooleanField(_("Send Email"), default=False)
    email_sent_at = models.DateTimeField(_("Email Sent Date"), blank=True, null=True)

    class Meta:
        db_table = "notification"
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_type_display()}: {self.subject[:20]}"

    @property
    def minutes_ago(self):
        diff = timezone.now() - self.created_at
        return int(diff.total_seconds() // 60)

    @property
    def type_enum(self):
        return self.NotificationType(self.type)
