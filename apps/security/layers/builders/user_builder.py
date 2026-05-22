import unicodedata

from django.contrib.auth.models import Group
from django.utils import timezone

from apps.security.models import Person, User


class UserBuilder:
    def __init__(self, user=None):
        self.user = user
        self.person = None

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

    def update_password(self, new_password):
        self.user.set_password(new_password)
        self.user.force_password = False
        self.user.last_password_change = timezone.now()
        self.user.save(update_fields=["password", "force_password", "last_password_change"])
        return self

    def build(self):
        return self.user
