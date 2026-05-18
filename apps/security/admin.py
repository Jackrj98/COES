from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from apps.core.mixins import BaseAdminMixin
from apps.security.models.users import Person, User


@admin.register(User)
class UserAdmin(UserAdmin, BaseAdminMixin):
    ordering = ("-created_at",)
    readonly_fields = ("last_login",)
    filter_horizontal = ("groups", "user_permissions")
    list_display = ("external_id", "username", "email", "email_verified", "force_password")
    list_filter = ("is_staff", "email_verified", "is_active", "force_password", "is_superuser")
    search_fields = (
        "email",
        "username",
        "external_id",
        "person__last_name",
        "person__document_number",
    )

    add_fieldsets = (
        (
            _("Credentials"),
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "username",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
        (_("Groups and Permissions"), {"fields": ("groups", "user_permissions")}),
    )

    fieldsets = (
        (
            _("User Information"),
            {
                "classes": ("wide",),
                "fields": (
                    ("email", "username"),
                    "password",
                    ("is_staff", "is_active", "is_superuser"),
                    ("email_verified", "force_password", "last_password_change"),
                    "person",
                ),
            },
        ),
        (
            _("Groups and Permissions"),
            {
                "classes": ("collapse", "wide"),
                "fields": ("groups", "user_permissions"),
            },
        ),
        (
            _("Audit Information"),
            {
                "classes": ("collapse", "wide"),
                "fields": (
                    "external_id",
                    "last_login",
                    ("created_at", "created_by"),
                    ("updated_at", "updated_by"),
                    "deleted_at",
                ),
            },
        ),
    )

@admin.register(Person)
class PersonAdmin(BaseAdminMixin):
    ordering = ("-created_at",)
    readonly_fields = ("age_display",)
    search_fields = ("last_name", "document_number", "external_id")
    list_filter = ("gender", "is_active")

    list_display = (
        "external_id",
        "full_name_display",
        "document_number",
        "age_display",
        "birth_date",
        "gender",
        "phone",
        "is_active",
    )


    @admin.display(description=_("Full Name"), ordering="last_name")
    def full_name_display(self, obj):
        return obj.full_name


    @admin.display(description=_("Age"))
    def age_display(self, obj):
        return obj.age_display

