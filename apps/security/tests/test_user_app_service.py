from unittest.mock import MagicMock, patch

import pytest
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from pydantic import ValidationError, ValidationError as PydanticValidationError

from apps.security.layers.applications import UserAppService
from apps.security.models import User


class TestUserAppService:
    @pytest.fixture
    def service(self):
        return UserAppService()

    @pytest.fixture
    def mock_user(self):
        user = MagicMock(spec=User)
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        user.external_id = "123e4567-e89b-12d3-a456-426614174000"
        return user

    @pytest.fixture
    def valid_registration_payload(self):
        return {
            "username": "2222222222",
            "email": "test@example.com",
            "password": "Password123!",
            "first_name": "Test",
            "last_name": "User",
            "document_number": "2222222222",
            "phone": "+593987654321",
            "groups": ["specialist"],
        }

    @pytest.fixture
    def valid_update_payload(self):
        return {
            "first_name": "Updated",
            "last_name": "Name",
            "document_number": "1137882666",
            "phone": "+593999999999",
        }

    # --- Tests retrieve_groups ---

    @patch("apps.security.layers.applications.user_service.apps.get_model")
    def test_retrieve_groups_success(self, mock_get_model, service):
        """Test retrieve groups successfully."""
        mock_group = MagicMock()
        mock_group.name = "specialist"
        mock_group.__str__.return_value = "specialist"

        mock_group_model = MagicMock()
        mock_group_model.objects.all.return_value = [mock_group]
        mock_get_model.return_value = mock_group_model

        result = service.retrieve_groups()

        assert result == [("specialist", "specialist")]
        mock_get_model.assert_called_once_with("auth", "Group")

    @patch("apps.security.layers.applications.user_service.apps.get_model")
    def test_retrieve_groups_exception(self, mock_get_model, service):
        """Test retrieve groups when exception occurs."""
        mock_get_model.side_effect = Exception("Database error")

        result = service.retrieve_groups()

        assert result == []

    # --- Tests register_user ---

    @pytest.mark.django_db
    @patch("apps.security.layers.applications.user_service.UserBuilder")
    def test_register_user_success(self, mock_builder_class, service, valid_registration_payload):
        """Test successful user registration."""
        mock_builder = mock_builder_class.return_value
        mock_builder.create_account.return_value = mock_builder
        mock_builder.add_person_details.return_value = mock_builder
        mock_builder.assign_groups.return_value = mock_builder
        mock_builder.build.return_value = MagicMock(spec=User)

        result = service.register_user(valid_registration_payload)

        assert result == mock_builder.build.return_value
        mock_builder.create_account.assert_called_once_with(
            username=valid_registration_payload["username"],
            email=valid_registration_payload["email"],
            password=valid_registration_payload["password"],
        )

    @pytest.mark.django_db
    def test_register_user_invalid_payload(self, service, caplog):
        """Test registration with an invalid payload."""
        with pytest.raises(PydanticValidationError):
            service.register_user({})
        assert "Validation error" in caplog.text

    @pytest.mark.django_db
    @patch("apps.security.layers.applications.user_service.UserBuilder")
    def test_register_user_integrity_error(
        self, mock_builder_class, service, valid_registration_payload
    ):
        """Test registration with integrity error (duplicate user)."""
        mock_builder = mock_builder_class.return_value
        mock_builder.create_account.side_effect = IntegrityError("Duplicate key")

        with pytest.raises(IntegrityError):
            service.register_user(valid_registration_payload)

    @pytest.mark.django_db
    @patch("apps.security.layers.applications.user_service.UserBuilder")
    def test_register_user_general_exception(
        self, mock_builder_class, service, valid_registration_payload, caplog
    ):
        """Test registration with general exception."""
        mock_builder = mock_builder_class.return_value
        mock_builder.create_account.side_effect = Exception("Unexpected error")

        with pytest.raises(Exception, match="Unexpected error"):
            service.register_user(valid_registration_payload)
        assert "Error creating user" in caplog.text

    # --- Tests update_user ---

    @patch("apps.security.layers.applications.user_service.UserBuilder")
    def test_update_user_success(
        self, mock_builder_class, service, mock_user, valid_update_payload
    ):
        mock_builder_instance = MagicMock()
        mock_builder_class.return_value = mock_builder_instance

        mock_builder_instance.update_person_details.return_value = mock_builder_instance
        mock_builder_instance.build.return_value = mock_user

        service.builder = mock_builder_class

        result = service.update_user(mock_user, valid_update_payload)

        assert result == mock_user
        mock_builder_instance.update_person_details.assert_called_once_with(
            first_name=valid_update_payload["first_name"],
            last_name=valid_update_payload["last_name"],
            document_number=valid_update_payload["document_number"],
            phone=valid_update_payload["phone"],
        )

    @patch("apps.security.layers.applications.user_service.UserBuilder")
    def test_update_user_validation_error(self, mock_builder_class, service, mock_user, caplog):
        mock_instance = MagicMock()
        mock_builder_class.return_value = mock_instance
        mock_instance.update_person_details.side_effect = ValidationError.from_exception_data(
            title="BaseUserDTO",
            line_errors=[
                {
                    "type": "value_error",
                    "loc": ("first_name",),
                    "msg": "Value error",
                    "input": "invalid",
                    "ctx": {"error": "Value error"},
                }
            ],
        )

        valid_payload = {"first_name": "A", "last_name": "B", "document_number": "1", "phone": "1"}

        with pytest.raises(ValidationError):
            service.update_user(mock_user, valid_payload)

        assert "Validation error" in caplog.text

    # --- Tests update_status ---

    @patch("apps.security.layers.applications.user_service.UserBuilder")
    def test_update_status_success(self, mock_builder_class, service, mock_user):
        """Test successful status update."""
        mock_builder_instance = MagicMock()
        mock_builder_class.return_value = mock_builder_instance

        mock_builder_instance.change_status.return_value = mock_builder_instance
        mock_builder_instance.build.return_value = mock_user

        service.builder = mock_builder_class
        mock_user.status = "ENABLED"

        result = service.update_status(mock_user)

        assert result == mock_user
        mock_builder_instance.change_status.assert_called_once()

    @patch("apps.security.layers.applications.user_service.UserBuilder")
    def test_update_status_validation_error(self, mock_builder_class, service, mock_user, caplog):
        """Test the update status and log the error."""
        mock_instance = MagicMock()
        mock_builder_class.return_value = mock_instance

        service.builder = mock_builder_class

        mock_instance.change_status.side_effect = ValueError("Invalid status")

        with pytest.raises(ValueError, match="Invalid status"):
            service.update_status(mock_user)

        assert "Error updating status: Invalid status" in caplog.text

    # --- Tests update_password ---

    @patch("apps.security.layers.applications.user_service.UserBuilder")
    def test_update_password_success(self, mock_builder_class, service, mock_user):
        """Test a successful password update."""
        mock_builder_instance = MagicMock()
        mock_builder_class.return_value = mock_builder_instance
        service.builder = mock_builder_class

        mock_builder_instance.update_password.return_value = mock_builder_instance
        mock_builder_instance.build.return_value = mock_user

        payload = {
            "new_password": "NewPassword123!",
            "current_password": "OldPassword123!",
            "confirm_password": "NewPassword123!",
        }

        result = service.update_password(mock_user, payload)

        assert result == mock_user
        mock_builder_instance.update_password.assert_called_once_with(
            new_password="NewPassword123!"
        )

    @patch("apps.security.layers.applications.user_service.UserBuilder")
    def test_update_password_permission_denied(self, mock_builder_class, service, mock_user):
        """Test password update with permission denied."""
        other_user = MagicMock(id=2, username="other")

        payload = {
            "new_password": "NewPassword123!",
            "current_password": "OldPassword123!",
            "confirm_password": "NewPassword123!",
            "user": other_user,
        }

        with pytest.raises(
            PermissionDenied, match="You are not authorized to change this password"
        ):
            service.update_password(mock_user, payload)

    @patch("apps.security.layers.applications.user_service.UserBuilder")
    def test_update_password_with_target_user(self, mock_builder_class, service, mock_user):
        """Test password update when the target user is explicitly provided and matches."""
        mock_builder = mock_builder_class.return_value
        mock_builder.update_password.return_value = mock_builder
        mock_builder.build.return_value = mock_user

        payload = {
            "new_password": "NewPassword123!",
            "current_password": "OldPassword123!",
            "confirm_password": "NewPassword123!",
            "user": mock_user,
        }

        result = service.update_password(mock_user, payload)

        assert result == mock_user

    def test_update_password_invalid_dto(self, service, mock_user, caplog):
        """Test password update with invalid DTO data."""
        payload = {
            "new_password": "New",  # Too short
            "current_password": "Old",
            "confirm_password": "Different",  # Doesn't match
        }

        with pytest.raises(PydanticValidationError):
            service.update_password(mock_user, payload)
        assert "Validation error" in caplog.text

    # --- Tests reset_password ---

    @patch("apps.security.layers.applications.user_service.UserBuilder")
    def test_reset_password_success(self, mock_builder_class, service, mock_user):
        """Test successful password reset."""
        mock_builder_instance = MagicMock()
        mock_builder_class.return_value = mock_builder_instance

        mock_builder_instance.reset_password.return_value = mock_builder_instance
        mock_builder_instance.build.return_value = mock_user

        service.builder = mock_builder_class
        new_password = "NewSecurePass123"
        result = service.reset_password(mock_user, new_password)

        assert result == mock_user
        mock_builder_instance.reset_password.assert_called_once_with(new_password=new_password)

    @patch("apps.security.layers.applications.user_service.UserBuilder")
    def test_reset_password_validation_error(self, mock_builder_class, service, mock_user, caplog):
        """Test password reset with a validation error."""
        mock_instance = MagicMock()
        mock_builder_class.return_value = mock_instance

        mock_instance.reset_password.side_effect = PydanticValidationError.from_exception_data(
            title="Invalid password",
            line_errors=[
                {
                    "type": "value_error",
                    "loc": ("password",),
                    "msg": "Value error",
                    "input": "weak",
                    "ctx": {"error": "Value error"},
                }
            ],
        )

        service.builder = mock_builder_class

        with pytest.raises(PydanticValidationError):
            service.reset_password(mock_user, "weak")

        assert any("Validation error" in record.message for record in caplog.records)

    # --- Tests retrieve_users ---

    @patch("apps.security.layers.applications.user_service.DatatableSearch")
    def test_retrieve_users_success(self, mock_dt, service):
        """Test successful user retrieval."""
        mock_params = MagicMock()
        mock_qs = MagicMock()
        mock_params.items = mock_qs
        mock_annotated = MagicMock()
        mock_qs.annotate.return_value = mock_annotated

        expected_result = [
            {
                "external_id": "123e4567-e89b-12d3-a456-426614174000",
                "username": "testuser",
                "email": "test@example.com",
                "status": 1,
                "is_active": True,
                "created_at": "2024-01-01",
                "created_by": "admin",
                "updated_at": "2024-01-01",
                "person__first_name": "Test",
                "person__last_name": "User",
                "person__document_number": "1234567890",
                "person__phone": "+593999999999",
                "group_name": "specialist, admin",
            }
        ]

        mock_annotated.values.return_value = expected_result
        mock_params.result.return_value = expected_result

        result = service.retrieve_users(mock_params)

        assert result == expected_result
        mock_dt.retrieve_users.assert_called_once_with(mock_params)
        mock_qs.annotate.assert_called_once()
        mock_params.result.assert_called_once()

    @patch("apps.security.layers.applications.user_service.DatatableSearch")
    def test_retrieve_users_empty_result(self, mock_dt, service):
        """Test retrieve users with empty result."""
        mock_params = MagicMock()
        mock_qs = MagicMock()
        mock_params.items = mock_qs
        mock_annotated = MagicMock()
        mock_qs.annotate.return_value = mock_annotated
        mock_annotated.values.return_value = []
        mock_params.result.return_value = []

        result = service.retrieve_users(mock_params)

        assert result == []

    @patch("apps.security.layers.applications.user_service.DatatableSearch")
    def test_retrieve_users_exception(self, mock_dt, service, caplog):
        """Test retrieve users when exception occurs."""
        mock_dt.retrieve_users.side_effect = Exception("DB Connection Error")

        result = service.retrieve_users(MagicMock())

        assert result == []
        assert "Failed to fetch users" in caplog.text

    # --- Tests para generate_password ---

    def test_generate_password_default_length(self, service):
        """Test password generation with the default length."""
        password = service.generate_password()
        assert len(password) == 8
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" for c in password)

    def test_generate_password_custom_length(self, service):
        """Test password generation with a custom length."""
        lengths = [6, 10, 12, 16, 20]
        for length in lengths:
            password = service.generate_password(length=length)
            assert len(password) == length
            assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" for c in password)

    def test_generate_password_randomness(self, service):
        """Test that generated passwords are random/different."""
        passwords = [service.generate_password() for _ in range(10)]
        assert len(set(passwords)) > 1

    def test_generate_password_only_uppercase_and_digits(self, service):
        """Test that password only contains uppercase letters and digits."""
        password = service.generate_password(length=50)
        assert (
            password.isupper()
            or password.isdigit()
            or all(c.isupper() or c.isdigit() for c in password)
        )
        assert not any(c.islower() for c in password)
        assert not any(not c.isalnum() for c in password)
