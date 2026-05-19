import logging

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.core.layers import BaseAppService
from apps.security.models import Person, User

logger = logging.getLogger(__name__)


class UserAppService(BaseAppService):
    def __init__(self):
        super().__init__(User)
        self.person = Person

    def _clean_data(self, data):
        required_fields = ["email", "first_name", "last_name", "document_number", "phone"]
        self.validate_required_fields(required_fields, data)

        return {
            "email": self.normalize_data(data["email"], remove_spaces=True),
            "first_name": self.normalize_data(data["first_name"]),
            "last_name": self.normalize_data(data["last_name"]),
            "document_number": str(
                self.normalize_data(data["document_number"], remove_spaces=True)
            ),
            "phone": str(self.normalize_data(data["phone"], remove_spaces=True)),
        }

    def create_person(self, data):
        try:
            cleaned_data = self._clean_data(data)
            return self.person.objects.create(
                first_name=cleaned_data["first_name"],
                last_name=cleaned_data["last_name"],
                document_number=cleaned_data["document_number"],
                phone=cleaned_data["phone"],
            )
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error creating person: {e}")
            raise

    @transaction.atomic
    def create_user(self, data):
        try:
            person = self.create_person(data)
            cleaned_data = self._clean_data(data)
            email = cleaned_data.get("email")
            document_number = cleaned_data.get("document_number")
            instance = self.model.objects.create_user(
                username=document_number,
                email=email,
                password=document_number,
                person_id=person.id,
            )

            group = Group.objects.get_or_create(name="specialist", defaults={"name": "specialist"})[
                0
            ]
            instance.groups.add(group.pk)
            instance.save()
            return instance
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise
