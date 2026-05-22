import pytest
from unittest.mock import MagicMock, patch
from django.core.exceptions import PermissionDenied
from pydantic import ValidationError
from redis.commands.search import document

from apps.security.layers.applications import UserAppService
from apps.security.utils.utils import generate_ecuadorian_id


class TestUserAppService:
    @pytest.fixture
    def service(self):
        return UserAppService()


    @pytest.mark.django_db
    @patch("apps.security.layers.applications.user_service.UserBuilder")
    def test_register_user_success(self, mock_builder_class, service):
        mock_builder = mock_builder_class.return_value
        mock_builder.create_account.return_value = mock_builder
        mock_builder.add_person_details.return_value = mock_builder
        mock_builder.assign_groups.return_value = mock_builder
        mock_builder.build.return_value = "new_user_object"

        payload = {
            "username": "2222222222",
            "email": "test@example.com",
            "password": "Password123!",
            "first_name": "Test",
            "last_name": "User",
            "document_number": "2222222222",
            "phone": "+593987654321",
            "groups": ["specialist"],
        }

        result = service.register_user(payload)
        assert result == "new_user_object"
    @pytest.mark.django_db
    def test_register_user_invalid_payload(self, service, caplog):
        with pytest.raises(ValidationError):
            service.register_user({})
        assert "Validation error" in caplog.text


    @patch("apps.security.layers.applications.user_service.UserBuilder")
    def test_update_password_permission_denied(self, mock_builder_class, service):
        request_user = MagicMock(id=1)
        other_user = MagicMock(id=2)

        payload = {
            "new_password": "NewPassword123!",
            "current_password": "OldPassword123!",
            "confirm_password": "NewPassword123!",
            "user": other_user,
        }

        with pytest.raises(PermissionDenied):
            service.update_password(request_user, payload)

    @patch("apps.security.layers.applications.user_service.UserBuilder")
    def test_update_password_success(self, mock_builder_class, service):
        user = MagicMock()
        mock_builder = mock_builder_class.return_value
        mock_builder.update_password.return_value = mock_builder
        mock_builder.build.return_value = True

        payload = {
            "new_password": "NewPassword123!",
            "current_password": "OldPassword123!",
            "confirm_password": "NewPassword123!",
        }

        result = service.update_password(user, payload)
        assert result is True
        mock_builder.update_password.assert_called_with("NewPassword123!")

    def test_update_password_invalid_dto(self, service, caplog):
        user = MagicMock()
        payload = {
            "new_password": "New",
            "current_password": "Old",
            "confirm_password": "Different",
        }

        with pytest.raises(ValidationError):
            service.update_password(user, payload)
        assert "Validation error" in caplog.text

    # --- Tests de Consulta ---

    @patch("apps.security.layers.applications.user_service.DatatableSearch")
    def test_retrieve_users_success(self, mock_dt, service):
        # Setup del mock
        mock_params = MagicMock()
        mock_qs = MagicMock()
        mock_params.items = mock_qs
        mock_qs.annotate.return_value = mock_qs
        mock_qs.values.return_value = [{"username": "testuser"}]
        mock_params.result.return_value = [{"username": "testuser"}]

        result = service.retrieve_users(mock_params)

        assert result == [{"username": "testuser"}]
        mock_dt.retrieve_users.assert_called_once()

    @patch("apps.security.layers.applications.user_service.DatatableSearch")
    def test_retrieve_users_exception(self, mock_dt, service, caplog):
        mock_dt.retrieve_users.side_effect = Exception("DB Error")

        result = service.retrieve_users(MagicMock())

        assert result == []
        assert "Failed to fetch users" in caplog.text
