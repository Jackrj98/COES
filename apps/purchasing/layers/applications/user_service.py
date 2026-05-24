import logging
import random
import string

from django.apps import apps
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
from apps.security.models import Person, User

logger = logging.getLogger(__name__)


class UserAppService(BaseAppService):
    """Service responsible for handling user-related operations."""

    def __init__(self):
        super().__init__(User)
        self.person = Person
        self.builder = UserBuilder

    @staticmethod
    def retrieve_groups():
        try:
            Group = apps.get_model("auth", "Group")
            groups = Group.objects.all()
            return [(group.name, _(group.name)) for group in groups]
        except Exception:
            return []

    @transaction.atomic
    def register_user(self, payload):
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
        except IntegrityError:
            raise
        except ValidationError as e:
            logger.warning(f"Validation error for payload: {e.json()}")
            raise
        except Exception as e:
            logger.error(f"Error creating user: {e}", exc_info=True)
            raise

    def update_user(self, user, payload):
        try:
            dto = BaseUserDTO(**payload)
            return (
                self.builder(user=user)
                .update_person_details(
                    first_name=dto.first_name,
                    last_name=dto.last_name,
                    document_number=dto.document_number,
                    phone=dto.phone,
                )
                .build()
            )
        except ValidationError as e:
            logger.warning(f"Validation error for payload: {e.json()}")
            raise
        except Exception as e:
            logger.error(f"Error update user: {e}", exc_info=True)
            raise

    def update_status(self, user):
        try:
            return self.builder(user=user).change_status().build()
        except (ValidationError, ValueError) as e:
            logger.warning(f"Error updating status: {e}")
            raise
        except Exception as e:
            logger.error(f"Error update status of user: {e}", exc_info=True)
            raise

    def update_password(self, request_user, payload):
        data = payload.copy()
        target_user = data.get("user", request_user)

        try:
            if not (request_user == target_user):
                raise PermissionDenied(_("You are not authorized to change this password"))

            data["user"] = target_user
            dto = UserPasswortDTO(**data)
            return (
                self.builder(user=dto.user).update_password(new_password=dto.new_password).build()
            )
        except ValidationError as e:
            logger.warning(f"Validation error: {e.errors()}")
            raise
        except Exception as e:
            username = getattr(request_user, "username", "unknown")
            logger.error(f"Error updating password for {username}: {e}", exc_info=True)
            raise

    def reset_password(self, request_user, password):
        try:
            return self.builder(user=request_user).reset_password(new_password=password).build()
        except ValidationError as e:
            logger.warning(f"Validation error: {e.errors()}")
            raise
        except Exception as e:
            username = getattr(request_user, "username", "unknown")
            logger.error(f"Error updating password for {username}: {e}", exc_info=True)
            raise

    @staticmethod
    def retrieve_users(params):
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
            return []

    @staticmethod
    def generate_password(length=8):
        return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))
