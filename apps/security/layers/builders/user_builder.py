import unicodedata

from django.contrib.auth.models import Group
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.security.models import Person, User


class UserBuilder:
    def __init__(self, user=None):
        self.user = user
        self.person = getattr(user, "person", None)

    @staticmethod
    def _normalize_string(value: str) -> str:
        if not value:
            return ""
        normalized = unicodedata.normalize("NFKD", value).encode("ASCII", "ignore").decode("utf-8")
        return normalized.strip().lower()

    def create_account(self, username, email, password):
        username = self._normalize_string(username)
        self.user = User.objects.create_user(
            username=username, email=email.lower(), password=password, force_password=True
        )
        return self

    def add_person_details(self, first_name, last_name, document_number, phone):
        self.person = Person.objects.create(
            first_name=first_name.strip().title(),
            last_name=last_name.strip().title(),
            document_number=document_number.strip().upper(),
            phone=phone.strip(),
        )

        self.user.person = self.person
        self.user.save(update_fields=["person"])
        return self

    def assign_groups(self, group_names):
        groups = Group.objects.filter(name__in=group_names)
        self.user.groups.set(groups)
        return self

    def change_status(self):
        current = self.user.status
        Status = self.user.Status

        statuses = {
            Status.ENABLED: {"status": Status.DISABLED.value, "is_active": False},
            Status.DISABLED: {"status": Status.ENABLED.value, "is_active": True},
            Status.LOCKED: {
                "status": Status.ENABLED.value,
                "is_active": True,
                "locked_at": None,
                "failed_login_attempts": 0,
            },
        }

        if current not in statuses:
            raise ValueError(_(f"Invalid user state for the transition: {current}"))

        transition = statuses[current]
        self.user.status = transition["status"]
        self.user.is_active = transition["is_active"]

        update_fields = ["is_active", "status"]
        if "locked_at" in transition:
            self.user.locked_at = transition["locked_at"]
            self.user.failed_login_attempts = transition["failed_login_attempts"]
            update_fields.append("locked_at")
            update_fields.append("failed_login_attempts")

        self.user.save(update_fields=update_fields)
        return self

    def update_person_details(self, first_name, last_name, document_number, phone):
        self.person.first_name = first_name.strip().title()
        self.person.last_name = last_name.strip().title()
        self.person.document_number = document_number.strip().upper()
        self.person.phone = phone.strip()
        self.person.save(update_fields=["first_name", "last_name", "document_number", "phone"])
        return self

    def update_password(self, new_password):
        self.user.set_password(new_password)
        self.user.force_password = False
        self.user.last_password_change = timezone.now()
        self.user.save(update_fields=["password", "force_password", "last_password_change"])
        return self

    def reset_password(self, new_password):
        self.user.is_active = True
        self.user.locked_at = None
        self.user.force_password = True
        self.user.failed_login_attempts = 0
        self.user.status = self.user.Status.ENABLED.value
        self.user.last_password_change = timezone.now()

        self.user.set_password(new_password)

        self.user.save(
            update_fields=[
                "password",
                "is_active",
                "locked_at",
                "force_password",
                "failed_login_attempts",
                "status",
                "last_password_change",
            ]
        )

        return self

    def build(self):
        return self.user
