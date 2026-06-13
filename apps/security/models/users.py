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
# Person Model
# ─────────────────────────────────────────


class Person(AuditModel):
    """Represents a person with personal, identification, and contact details."""

    # Personal information
    first_name = models.CharField(
        _("First name"), max_length=75, validators=[MinLengthValidator(3), text_only]
    )
    last_name = models.CharField(
        _("Last name"), max_length=75, validators=[MinLengthValidator(3), text_only]
    )

    # Document information
    document_number = models.CharField(
        _("Document number"),
        unique=True,
        max_length=13,
        validators=[MinLengthValidator(10), django_id_validator],
    )

    # Contact information
    phone = models.CharField(_("Phone number"), max_length=15, validators=[MinLengthValidator(10)])

    class Meta:
        db_table = "person"
        verbose_name = _("Person")
        get_latest_by = "created_at"
        verbose_name_plural = _("People")
        ordering = ["last_name", "-created_at"]
        indexes = [
            models.Index(fields=["document_number"]),
            models.Index(fields=["last_name", "first_name"]),
        ]

    def __str__(self):
        return self.short_name

    @property
    def full_name(self):
        return f"{self.last_name.title()} {self.first_name.title()}"

    @property
    def short_name(self):
        last_name = capfirst(self.last_name.split()[0])
        first_name = capfirst(self.first_name.split()[0])
        return f"{last_name} {first_name}"

    @property
    def initials(self):
        return f"{self.first_name[0]}{self.last_name[0]}".upper()


# ─────────────────────────────────────────
# User Model
# ─────────────────────────────────────────


class User(AbstractBaseUser, AuditModel, PermissionsMixin):
    """Represents a user in the system."""

    class Status(models.IntegerChoices):
        ENABLED = 1, _("Enabled")
        DISABLED = 2, _("Disabled")
        LOCKED = 3, _("Locked")

        @property
        def style(self) -> dict:
            configs = {
                self.ENABLED.value: {"color": "success"},
                self.DISABLED.value: {"color": "secondary"},
                self.LOCKED.value: {"color": "danger"},
            }
            return configs[self.value]

        @property
        def color(self) -> str:
            return self.style["color"]

        @classmethod
        def get_ui_map(cls):
            return {item.value: {"color": item.color, "label": item.label} for item in cls}

    email = models.EmailField(_("Email address"), unique=True, max_length=255)
    username = models.CharField(
        _("Username"), unique=True, max_length=50, validators=[MinLengthValidator(5)]
    )

    is_staff = models.BooleanField(default=False)
    email_verified = models.BooleanField(_("Email verified"), default=False)
    force_password = models.BooleanField(_("Force password change"), default=False)
    last_password_change = models.DateField(_("Last password change"), default=timezone.now)

    status = models.PositiveSmallIntegerField(_("Status"), choices=Status, default=Status.ENABLED)
    failed_login_attempts = models.IntegerField(_("Failed login attempts"), default=0)
    locked_at = models.DateTimeField(_("Locked at"), null=True, blank=True)

    # Relationship
    person = models.OneToOneField(
        Person, on_delete=models.CASCADE, null=True, blank=True, related_name="user"
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        db_table = "user"
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ["-created_at"]
        get_latest_by = "created_at"
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["username"]),
        ]
        permissions = (("view_users", "Can view users list"),)

    def __str__(self):
        return str(self.username or self.email)

    @property
    def email_verified_display(self):
        """Return the email verification status."""
        return _("Verified") if self.email_verified else _("Not verified")

    @property
    def primary_group(self):
        return self.groups.order_by("name").first()

    @property
    def status_color(self):
        return self.Status(self.status).color

    # ── Helpers ─────────────────────────────────

    def has_group(self, group_name: str) -> bool:
        return self.groups.filter(name=group_name).exists()

    def verify_email(self) -> None:
        self.email_verified = True
        self.save(update_fields=["email_verified", "updated_at"])

    def get_absolute_url(self):
        return reverse("security:users:detail", kwargs={"external_id": self.external_id})


def get_default_expiration():
    return timezone.now() + timedelta(hours=24)


class UserToken(AuditModel):
    """Single-use token for email verification and password reset.
    Allows multiple active tokens per user at the same time
    (e.g., pending verification and password reset simultaneously).
     The status is determined at runtime—it is not stored in the database.
    """

    class TokenType(models.IntegerChoices):
        """List of token types."""

        EMAIL_VERIFY = 1, _("Email verification")
        PASSWORD_RESET = 2, _("Password reset")

    class TokenStatus(models.IntegerChoices):
        """List of token statuses."""

        PENDING = 1, _("Pending")
        USED = 2, _("Used")
        EXPIRED = 3, _("Expired")

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="tokens",
        verbose_name=_("User"),
    )
    token = models.CharField(
        _("Token"),
        max_length=255,
        unique=True,
        validators=[MaxLengthValidator(255)],
    )
    token_type = models.PositiveSmallIntegerField(_("Token type"), choices=TokenType)
    expires_at = models.DateTimeField(_("Expires at"), default=get_default_expiration)
    status = models.PositiveSmallIntegerField(
        _("Status"), choices=TokenStatus, default=TokenStatus.PENDING
    )
    used_at = models.DateTimeField(_("Used at"), null=True, blank=True)

    class Meta:
        db_table = "user_token"
        app_label = "security"
        ordering = ["-created_at"]
        verbose_name = _("User token")
        verbose_name_plural = _("User tokens")
        indexes = [
            models.Index(fields=["token"]),
            models.Index(fields=["user", "token_type"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"{self.user} — {self.get_token_type_display()} [{self.status}]"

    @property
    def is_used(self) -> bool:
        return self.used_at is not None

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    @property
    def is_valid(self) -> bool:
        return not self.is_used and not self.is_expired

    @property
    def current_status(self) -> str:
        if self.is_used:
            return str(self.TokenStatus.USED.label)
        if self.is_expired:
            return str(self.TokenStatus.EXPIRED.label)
        return str(self.TokenStatus.PENDING.label)

    # ── Helpers ─────────────────────────────────

    def consume(self) -> None:
        if not self.is_valid:
            raise ValueError(_("Token is no longer valid: %(status)s") % {"status": self.status})
        self.used_at = timezone.now()
        self.save(update_fields=["used_at", "updated_at"])

    @classmethod
    def generate(cls, user: User, token_type: int, ttl_minutes: int = 60):
        """Creates a new token for the user.

        Args:
            user:        The user to whom the token belongs.
            token_type:  EMAIL_VERIFY | PASSWORD_RESET
            ttl_minutes: Lifetime in minutes (default: 60).

        Returns:
            A saved UserToken instance.
        """
        return cls.objects.create(
            user=user,
            token=secrets.token_urlsafe(48),
            token_type=token_type,
            expires_at=timezone.now() + timedelta(minutes=ttl_minutes),
            created_by=user,
        )

    @classmethod
    def invalidate_previous(cls, user: User, token_type: int) -> int:
        """Invalidates (marks as used) all previous tokens
        of the same type to prevent active orphan tokens.
        Returns the number of invalidated tokens.
        """
        now = timezone.now()
        return cls.objects.filter(
            user=user, token_type=token_type, used_at__isnull=True, expires_at__gt=now
        ).update(used_at=now)
