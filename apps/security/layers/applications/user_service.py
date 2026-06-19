import logging
import random
import string

from django.contrib.auth.models import Group
from django.contrib.postgres.aggregates import StringAgg
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from pydantic import ValidationError

from apps.core.layers import BaseAppService
from apps.security.layers.builders import PersonBuilder, UserBuilder
from apps.security.layers.dto import DatatableSearch
from apps.security.models import User

logger = logging.getLogger(__name__)


class UserAppService(BaseAppService):
    """Service responsible for handling user-related operations."""

    def __init__(self):
        super().__init__(User)

    def retrieve_groups(self):
        """Retrieve all available groups."""
        try:
            from django.db import connection

            with connection.cursor() as cursor:
                table_name = "auth_group"

                if connection.vendor == "postgresql":
                    cursor.execute(
                        """
                                   SELECT EXISTS (
                                       SELECT FROM information_schema.tables
                                       WHERE table_name = %s
                                   );
                                   """,
                        [table_name],
                    )
                elif connection.vendor == "sqlite":
                    cursor.execute(
                        """
                                   SELECT name FROM sqlite_master
                                   WHERE type='table' AND name=?
                                   """,
                        [table_name],
                    )
                elif connection.vendor == "mysql":
                    cursor.execute(
                        """
                                   SELECT TABLE_NAME FROM information_schema.tables
                                   WHERE table_name = %s
                                   """,
                        [table_name],
                    )
                else:
                    # Fallback: intentar ejecutar una consulta simple
                    cursor.execute("SELECT 1 FROM auth_group LIMIT 1")
                    table_exists = True
                    return self._fetch_groups()

                result = cursor.fetchone()
                table_exists = bool(result and result[0])

            if not table_exists:
                logger.warning("auth_group table does not exist. Run migrations.")
                return []

            return self._fetch_groups()

        except Exception as e:
            logger.exception(f"Error retrieving groups: {e}")
            return []

    @staticmethod
    def _fetch_groups():
        """Helper method to fetch groups."""
        try:
            groups = Group.objects.all()
            return [(group.name, _(group.name)) for group in groups]
        except Exception as e:
            logger.exception(f"Error fetching groups: {e}")
            return []

    @staticmethod
    def retrieve_users(params):
        """Retrieve users for datatable."""
        fields = [
            "external_id",
            "username",
            "email",
            "status",
            "is_active",
            "created_at",
            "created_by",
            "updated_at",
            "person__first_name",
            "person__last_name",
            "person__document_number",
            "person__phone",
        ]
        try:
            DatatableSearch.retrieve_users(params)
            qs = params.items.annotate(group_name=StringAgg("groups__name", delimiter=", "))
            return params.result(list(qs.values(*fields, "group_name")))
        except Exception as e:
            logger.exception(f"Failed to fetch users: {e}")
            return params.result([]) if hasattr(params, "result") else []

    @staticmethod
    def generate_password(length=9):
        """Generate a random password."""
        return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))

    @staticmethod
    def _update_person(builder, data):
        return (
            builder.set_first_name(data.get("first_name"))
            .set_last_name(data.get("last_name"))
            .set_document_number(data.get("document_number"))
            .set_phone(data.get("phone"))
            .build()
        )

    @staticmethod
    def _update_user(builder, person, data):
        passwd = data.get("password", "")
        if len(passwd) < 8:
            raise ValueError(_("Password must be at least 8 characters long"))

        return (
            builder.set_username(person.document_number)
            .set_email(data.get("email"))
            .set_password(person.document_number)
            .set_person(person.id)
            .set_groups(data.get("groups"))
            .build()
        )

    @transaction.atomic
    def save_user(self, user=None, payload=None):
        user_builder = UserBuilder(user)
        person_builder = PersonBuilder(getattr(user, "person", None))

        try:
            person = self._update_person(person_builder, payload)
            user = self._update_user(user_builder, person, payload)
            return user
        except ValidationError as e:
            logger.warning(f"Validation error: {e.errors()}")
            raise e
        except Exception as e:
            logger.error("Failed to save user", exc_info=True)
            raise e

    def register_user(self, payload):
        return self.save_user(user=None, payload=payload)

    def update_user(self, instance, payload):
        if not instance:
            raise ValueError(_("User instance is required to update"))

        person = instance.person
        person_builder = PersonBuilder(person)
        return self._update_person(person_builder, payload)

    @staticmethod
    def update_status(instance):
        """Update user status."""
        if not instance:
            raise ValueError(_("User instance is required to update"))

        choices = User.Status
        current_state = instance.status

        transitions = {
            choices.ENABLED: {"status": choices.DISABLED.value, "is_active": False},
            choices.DISABLED: {"status": choices.ENABLED.value, "is_active": True},
            choices.LOCKED: {
                "status": choices.ENABLED.value,
                "is_active": True,
                "locked_at": None,
                "failed_login_attempts": 0,
            },
        }

        if current_state not in transitions:
            raise ValueError(_(f"Invalid user state for transition: {current_state}"))

        transition = transitions[current_state]
        builder = UserBuilder(user=instance)

        try:
            builder.set_status(transition["status"])
            builder.set_is_active(transition["is_active"])

            if current_state == choices.LOCKED:
                instance.locked_at = transition["locked_at"]
                instance.failed_login_attempts = transition["failed_login_attempts"]

            return builder.build()

        except Exception as e:
            logger.error(f"Error updating status for user {instance.id}: {e}", exc_info=True)
            raise

    @staticmethod
    def update_password(request_user, payload):
        """Update user password."""
        data = payload.copy()
        target_user = data.get("user", request_user)

        try:
            if request_user != target_user:
                raise PermissionDenied(_("You are not authorized to change this password"))
            if len(data.get("new_password", "")) < 8:
                raise ValueError(_("Password must be at least 8 characters long"))

            data["user"] = target_user
            builder = UserBuilder(user=target_user)
            user = builder.set_password(payload.get("new_password")).user
            user.save(update_fields=["password", "force_password", "last_password_change"])
            return user

        except ValidationError as e:
            logger.warning(f"Validation error: {e.errors()}")
            raise
        except PermissionDenied:
            raise
        except Exception as e:
            username = getattr(request_user, "username", "unknown")
            logger.error(f"Error updating password for {username}: {e}", exc_info=True)
            raise

    @staticmethod
    def reset_password(request_user, password):
        """Reset user password."""
        builder = UserBuilder(user=request_user)
        try:
            if len(password) < 8:
                raise ValueError(_("Password must be at least 8 characters long"))
            user = (
                builder.set_password(password)
                .set_force_password(True)
                .set_status(User.Status.ENABLED)
                .set_is_active(True)
            ).user

            user.locked_at = None
            user.force_password = True
            user.failed_login_attempts = 0
            user.last_password_change = timezone.now()

            user.save(
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
            return user
        except ValidationError as e:
            logger.warning(f"Validation error: {e.errors()}")
            raise
        except Exception as e:
            username = getattr(request_user, "username", "unknown")
            logger.error(f"Error resetting password for {username}: {e}", exc_info=True)
            raise
