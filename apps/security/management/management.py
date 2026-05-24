from django.contrib.auth.models import BaseUserManager, Group
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Manages User creation, modification, and retrieval in the system.

    Provides helper methods to create standard user accounts, superuser accounts,
    and retrieve user instances based on natural keys. This class extends the
    `BaseUserManager`, adding custom logic for user creation and management.
    """

    def _create_user(self, username, email, password, **extra_fields):
        if not username:
            raise ValueError(_("Username is required."))

        if not email:
            raise ValueError(_("Email is required."))

        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username: str, email: str, password: str = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(username, email, password, **extra_fields)

    def create_superuser(self, username: str, email: str, password: str = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("email_verified", True)
        extra_fields.setdefault("force_password", False)

        if not extra_fields.get("is_staff"):
            raise ValueError(_("Superuser must have is_staff=True."))
        if not extra_fields.get("is_superuser"):
            raise ValueError(_("Superuser must have is_superuser=True."))

        user = self._create_user(username, email, password, **extra_fields)
        group, __ = Group.objects.get_or_create(name="administrator")
        user.groups.add(group)
        return user

    def get_by_natural_key(self, username):
        """Allows login by username or email."""
        return self.get(models.Q(username=username) | models.Q(email=username))
