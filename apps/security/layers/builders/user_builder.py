import unicodedata

from django.contrib.auth.models import Group
from django.utils import timezone

from apps.security.models import User


class UserBuilder:
    def __init__(self, user=None):
        self.user = user or User()
        self._pending_groups = None
        self.person = getattr(user, "person", None)

    @staticmethod
    def _normalize_string(value: str) -> str:
        if not value:
            return ""
        normalized = unicodedata.normalize("NFKD", value).encode("ASCII", "ignore").decode("utf-8")
        return normalized.strip().lower()

    def set_username(self, username):
        self.user.username = self._normalize_string(username)
        return self

    def set_email(self, email):
        self.user.email = email.lower()
        return self

    def set_password(self, password):
        self.user.set_password(password)
        self.user.force_password = False
        self.user.last_password_change = timezone.now()
        return self

    def set_force_password(self, force_password):
        self.user.force_password = force_password
        return self

    def set_status(self, status):
        self.user.status = status
        if status in [self.user.Status.LOCKED, self.user.Status.DISABLED]:
            self.user.is_active = False
        return self

    def set_is_active(self, is_active):
        self.user.is_active = is_active
        return self

    def set_person(self, person_id):
        self.user.person_id = person_id
        return self

    def set_groups(self, group_names):
        self._pending_groups = group_names
        return self

    def build(self):
       # self.user.full_clean()
        if self.user.pk is None:
            self.user = User.objects.create_user(
                username=self.user.username,
                email=self.user.email,
                password=self.user.password,
                force_password=self.user.force_password,
                person_id=self.user.person_id,
            )
        else:
            self.user.save()

        if self._pending_groups is not None:
            groups = Group.objects.filter(name__in=self._pending_groups)
            self.user.groups.set(groups)

        return self.user
