from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import AuditModel

# ─────────────────────────────────────────
# Notification Model
# ─────────────────────────────────────────


class Notification(AuditModel):
    class TypeChoices(models.IntegerChoices):
        ALERT = 1, _("Alert")
        NOTIFICATION = 2, _("Notification")

    subject = models.CharField(_("Subject"), max_length=255)
    type = models.IntegerField(_("Type"), choices=TypeChoices, default=TypeChoices.NOTIFICATION)
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
