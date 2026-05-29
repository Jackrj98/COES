import logging
import random
import string

from django.contrib.auth.models import Group
from django.contrib.postgres.aggregates import StringAgg
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.utils.translation import gettext_lazy as _
from pydantic import ValidationError

from apps.core.layers import BaseAppService
from apps.security.layers.builders.user_builder import UserBuilder
from apps.security.layers.dto import (
    BaseUserDTO,
    DatatableSearch,
    UserPasswortDTO,
    UserRegistrationDTO,
)
from apps.security.models import User

logger = logging.getLogger(__name__)


class UserAppService(BaseAppService):
    """Service responsible for handling user-related operations."""

    def __init__(self):
        super().__init__(User)

    @staticmethod
    def retrieve_groups():
        """Retrieve all available groups."""
        try:
            groups = Group.objects.all()
            return [(group.name, _(group.name)) for group in groups]
        except Exception as e:
            logger.exception(f"Unexpected error retrieving groups: {e}")
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
    def generate_password(length=8):
        """Generate a random password."""
        return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))

    @staticmethod
    @transaction.atomic
    def register_user(payload):
        """Register a new user."""
        builder = UserBuilder()
        try:
            dto = UserRegistrationDTO(**payload)
            return (
                builder.create_account(
                    username=dto.username,
                    email=dto.email,
                    password=dto.password,
                )
                .add_person_details(
                    first_name=dto.first_name,
                    last_name=dto.last_name,
                    document_number=dto.document_number,
                    phone=dto.phone,
                )
                .assign_groups(dto.groups)
                .build()
            )
        except IntegrityError as e:
            logger.info(f"User registration failed - duplicate: {e}")
            raise
        except ValidationError as e:
            logger.warning(f"User registration failed - validation: {e.json()}")
            raise
        except Exception as e:
            logger.critical(f"CRITICAL: User registration crashed: {e}", exc_info=True)
            raise

    @staticmethod
    def update_user(user, payload):
        """Update user information."""
        builder = UserBuilder(user=user)
        try:
            dto = BaseUserDTO(**payload)
            return builder.update_person_details(
                first_name=dto.first_name,
                last_name=dto.last_name,
                document_number=dto.document_number,
                phone=dto.phone,
            ).build()
        except ValidationError as e:
            logger.warning(f"Validation error for payload: {e.json()}")
            raise
        except Exception as e:
            logger.error(f"Error updating user: {e}", exc_info=True)
            raise

    @staticmethod
    def update_status(user):
        """Update user status."""
        builder = UserBuilder(user=user)
        try:
            return builder.change_status().build()
        except (ValidationError, ValueError) as e:
            logger.warning(f"Error updating status: {e}")
            raise
        except Exception as e:
            logger.error(f"Error updating status: {e}", exc_info=True)
            raise

    @staticmethod
    def update_password(request_user, payload):
        """Update user password."""
        data = payload.copy()
        target_user = data.get("user", request_user)

        try:
            if request_user != target_user:
                raise PermissionDenied(_("You are not authorized to change this password"))

            data["user"] = target_user
            dto = UserPasswortDTO(**data)
            builder = UserBuilder(user=dto.user)

            return builder.update_password(new_password=dto.new_password).build()
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
            return builder.reset_password(new_password=password).build()
        except ValidationError as e:
            logger.warning(f"Validation error: {e.errors()}")
            raise
        except Exception as e:
            username = getattr(request_user, "username", "unknown")
            logger.error(f"Error resetting password for {username}: {e}", exc_info=True)
            raise
