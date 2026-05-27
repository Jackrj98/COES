from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError as PydanticValidationError

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

    @patch("apps.security.layers.applications.user_service.Group")
    def test_retrieve_groups_success(self, mock_group_model, service):
        mock_group = MagicMock()
        mock_group.name = "specialist"
        mock_group_model.objects.all.return_value = [mock_group]

        result = service.retrieve_groups()
        assert result == [("specialist", "specialist")]

    # --- Tests register_user ---

    @pytest.mark.django_db
    @patch("apps.security.layers.applications.user_service.UserBuilder")
    def test_register_user_success(self, mock_builder_class, service, valid_registration_payload):
        mock_instance = mock_builder_class.return_value

        mock_instance.create_account.return_value = mock_instance
        mock_instance.add_person_details.return_value = mock_instance
        mock_instance.assign_groups.return_value = mock_instance
        mock_instance.build.return_value = MagicMock(spec=User)

        result = service.register_user(valid_registration_payload)

        mock_instance.create_account.assert_called_once()
        assert result is not None

    @pytest.mark.django_db
    @patch("apps.security.layers.applications.UserAppService")
    def test_register_user_invalid_payload(self, mock_builder, service, caplog):
        with pytest.raises(PydanticValidationError):
            service.register_user({})
        assert "User registration failed - validation" in caplog.text

    @pytest.mark.django_db
    @patch("apps.security.layers.applications.user_service.UserBuilder")
    def test_register_user_general_exception(
        self, mock_builder_class, service, valid_registration_payload, caplog
    ):
        mock_instance = mock_builder_class.return_value
        mock_instance.create_account.side_effect = Exception("Unexpected error")

        with pytest.raises(Exception, match="Unexpected error"):
            service.register_user(valid_registration_payload)

        assert "CRITICAL: User registration crashed" in caplog.text

    # --- Tests update_user ---

    @patch("apps.security.layers.applications.UserAppService")
    def test_update_user_success(
        self, mock_builder_class, service, mock_user, valid_update_payload
    ):
        mock_builder = mock_builder_class.return_value
        mock_builder.update_person_details.return_value = mock_builder
        mock_builder.build.return_value = mock_user

        result = service.update_user(mock_user, valid_update_payload)
        assert result == mock_user

    # --- Tests update_status ---

    @patch("apps.security.layers.applications.user_service.UserBuilder")
    def test_update_status_success(self, mock_builder_class, service, mock_user):
        mock_builder = mock_builder_class.return_value
        mock_builder.change_status.return_value = mock_builder
        mock_builder.build.return_value = mock_user

        result = service.update_status(mock_user)
        assert result == mock_user

    # --- Tests update_password ---

    @patch("apps.security.layers.applications.user_service.UserBuilder")
    def test_update_password_success(self, mock_builder_class, service, mock_user):
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

    # --- Tests retrieve_users ---

    @patch("apps.security.layers.applications.user_service.DatatableSearch")
    def test_retrieve_users_success(self, mock_dt, service):
        mock_params = MagicMock()
        mock_qs = MagicMock()
        mock_params.items = mock_qs
        mock_params.result.return_value = []

        service.retrieve_users(mock_params)
        mock_dt.retrieve_users.assert_called_once()
