from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from apps.core.models import AuditModel
from django.utils.translation import gettext_lazy as _


class Person(AbstractBaseUser, AuditModel, PermissionsMixin):


    class Meta:
        db_table = "person"
        verbose_name = _("Person")
        verbose_name_plural = _("Persons")
        ordering = ["-created_at"]
        get_latest_by = "created_at"


class User(AbstractBaseUser, AuditModel, PermissionsMixin):

    email = models.EmailField()
    username = models.CharField()

    is_staff = models.BooleanField(default=False)
    force_password = models.BooleanField(_("Force password change"), default=False)
    date_change_password = models.DateField(_("Date change password"), auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        db_table = "user"
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ["-created_at"]
        get_latest_by = "created_at"

    def __str__(self):
        return str(self.username or self.email)