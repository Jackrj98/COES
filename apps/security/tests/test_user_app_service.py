import string
from unittest.mock import patch

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory

from apps.security.layers.applications.user_service import UserAppService
from apps.security.models import User
from apps.security.utils.utils import generate_ecuadorian_id


@pytest.mark.django_db
class TestUserAppService:
    """Test suite for UserAppService."""

    @pytest.fixture
    def service(self):
        """Fixture for UserAppService instance."""
        return UserAppService()

    @pytest.fixture
    def user_payload(self):
        """Fixture for user creation payload."""
        return {
            "first_name": "John",
            "last_name": "Doe",
            "document_number": "2222222222",
            "phone": "+593987654321",
            "email": "john.doe@example.com",
            "password": "Password123!",
            "groups": ["specialist"],
        }

    @pytest.fixture
    def admin_group(self):
        """Fixture for an admin group."""
        group, _ = Group.objects.get_or_create(name="administrator")
        return group

    @pytest.fixture
    def specialist_group(self):
        """Fixture for a specialist group."""
        group, _ = Group.objects.get_or_create(name="specialist")
        return group

    # --- retrieve_groups tests ---

    def test_retrieve_groups_success(self, service, admin_group, specialist_group):
        """Test retrieving all groups successfully."""
        groups = service.retrieve_groups()

        assert isinstance(groups, list)
        assert len(groups) >= 2
        assert ("administrator", "administrator") in groups
        assert ("specialist", "specialist") in groups

    def test_retrieve_groups_when_no_groups(self, service):
        """Test retrieving groups when none exist."""
        Group.objects.all().delete()
        groups = service.retrieve_groups()

        assert groups == []

    @patch("apps.security.layers.applications.user_service.Group.objects.all")
    def test_retrieve_groups_exception_handling(self, mock_all, service):
        """Test exception handling when retrieving groups."""
        mock_all.side_effect = Exception("Database error")
        groups = service.retrieve_groups()

        assert groups == []

    # --- retrieve_users tests ---
    def test_retrieve_users_success(self, service, user_payload):
        """Test retrieving users for datatable."""
        # Create a user
        user = service.register_user(user_payload)

        # Create a real request
        factory = RequestFactory()
        request = factory.get(
            "/users/",
            {
                "draw": "1",
                "start": "0",
                "length": "10",
                "search[value]": "",
                "order[0][column]": "0",
                "order[0][dir]": "asc",
                "columns[0][data]": "username",
            },
        )

        # Create proper mock params that mimics DataTableParams
        class MockParams:
            def __init__(self, request):
                self.request = request
                self.draw = 1
                self.length = 10
                self.start = 0
                self.search_value = ""
                self.order_column = "username"
                self.count = 0
                self.total = User.objects.count()
                self.items = None

            def init_items(self, queryset):
                """Initialize items with pagination and ordering."""
                self.count = queryset.count()
                queryset = queryset.order_by(self.order_column)
                self.items = queryset[self.start : self.start + self.length]
                return self.items

            def result(self, data):
                """Generate a result dictionary for DataTables."""
                return {
                    "data": data,
                    "draw": self.draw,
                    "recordsTotal": self.total,
                    "recordsFiltered": self.count,
                }

        params = MockParams(request)
        result = service.retrieve_users(params)

        assert "data" in result
        assert len(result["data"]) == 1
        assert result["data"][0]["username"] == user.username

    def test_retrieve_users_empty(self, service):
        """Test retrieving users when none exist."""

        class MockParams:
            def __init__(self):
                self.items = User.objects.none()

            def result(self, data):
                return []

        params = MockParams()
        result = service.retrieve_users(params)

        assert result == []

    def test_retrieve_users_exception_handling(self, service):
        """Test exception handling when retrieving users."""

        class MockParams:
            @property
            def items(self):
                raise Exception("Database error")

        params = MockParams()
        result = service.retrieve_users(params)

        assert result == []

    # --- generate_password tests ---

    def test_generate_password_default_length(self, service):
        """Test password generation with the default length."""
        password = service.generate_password()

        assert isinstance(password, str)
        assert len(password) == 9
        assert all(c in string.ascii_uppercase + string.digits for c in password)

    def test_generate_password_custom_length(self, service):
        """Test password generation with a custom length."""
        for length in [6, 10, 12, 16]:
            password = service.generate_password(length)
            assert len(password) == length

    def test_generate_password_randomness(self, service):
        """Test that generated passwords are random."""
        passwords = [service.generate_password() for _ in range(100)]
        # Should have at least 90% unique passwords
        unique_count = len(set(passwords))
        assert unique_count > 90

    # --- register_user tests ---

    def test_register_user_success(self, service, user_payload):
        """Test successful user registration."""
        user = service.register_user(user_payload)

        assert user.pk is not None
        assert user.username == user_payload["document_number"]
        assert user.email == user_payload["email"]
        assert user.person.first_name == user_payload["first_name"]
        assert user.person.last_name == user_payload["last_name"]
        assert user.person.document_number == user_payload["document_number"]
        assert user.person.phone == user_payload["phone"]
        assert user.is_active is True
        assert user.status == User.Status.ENABLED

    def test_register_user_with_groups(self, service, user_payload, specialist_group):
        """Test user registration with group assignment."""
        user = service.register_user(user_payload)

        assert user.groups.filter(name="specialist").exists()

    def test_register_user_duplicate_document_number(self, service, user_payload):
        """Test registration with duplicate document number."""
        service.register_user(user_payload)

        with pytest.raises(Exception):  # IntegrityError expected
            service.register_user(user_payload)

    def test_register_user_missing_required_fields(self, service):
        """Test registration with missing required fields."""
        incomplete_payload = {
            "first_name": "John",
            # Missing last_name, document_number, etc.
        }

        with pytest.raises(Exception):
            service.register_user(incomplete_payload)

    # --- update_user tests ---

    def test_update_user_success(self, service, user_payload):
        """Test successful user update."""
        user = service.register_user(user_payload)

        update_payload = {
            "first_name": "Jane",
            "last_name": "Smith",
            "phone": "+593999999999",
            "document_number": "2222222222",
        }

        updated_person = service.update_user(user, update_payload)

        assert updated_person.first_name == "Jane"
        assert updated_person.last_name == "Smith"
        assert updated_person.phone == "+593999999999"

    def test_update_user_without_instance(self, service):
        """Test update without providing user instance."""
        with pytest.raises(ValueError, match="User instance is required to update"):
            service.update_user(None, {})

    # --- update_status tests ---

    def test_update_status_from_enabled_to_disabled(self, service, user_payload):
        """Test status transition from ENABLED to DISABLED."""
        user = service.register_user(user_payload)
        assert user.status == User.Status.ENABLED
        assert user.is_active is True

        updated_user = service.update_status(user)

        assert updated_user.status == User.Status.DISABLED
        assert updated_user.is_active is False

    def test_update_status_from_disabled_to_enabled(self, service, user_payload):
        """Test status transition from DISABLED to ENABLED."""
        user = service.register_user(user_payload)
        user.status = User.Status.DISABLED
        user.is_active = False
        user.save()

        updated_user = service.update_status(user)

        assert updated_user.status == User.Status.ENABLED
        assert updated_user.is_active is True

    def test_update_status_from_locked_to_enabled(self, service, user_payload):
        """Test status transition from LOCKED to ENABLED."""
        user = service.register_user(user_payload)
        user.status = User.Status.LOCKED
        user.locked_at = "2024-01-01"
        user.failed_login_attempts = 5
        user.save()

        updated_user = service.update_status(user)

        assert updated_user.status == User.Status.ENABLED
        assert updated_user.is_active is True
        assert updated_user.locked_at is None
        assert updated_user.failed_login_attempts == 0

    def test_update_status_invalid_state(self, service, user_payload):
        """Test status update with invalid state."""
        user = service.register_user(user_payload)
        user.status = 6
        user.save()

        with pytest.raises(ValueError, match="Invalid user state for transition"):
            service.update_status(user)

    def test_update_status_without_instance(self, service):
        """Test status update without user instance."""
        with pytest.raises(ValueError, match="User instance is required to update"):
            service.update_status(None)

    # --- update_password tests ---

    def test_update_password_success(self, service, user_payload):
        """Test successful password update."""
        user = service.register_user(user_payload)
        old_password_hash = user.password

        payload = {"user": user, "new_password": "NewPassword123!"}

        updated_user = service.update_password(user, payload)

        assert updated_user.password != old_password_hash
        assert updated_user.force_password is False
        assert updated_user.last_password_change is not None

    def test_update_password_unauthorized(self, service, user_payload):
        """Test password update by an unauthorized user."""
        user1 = service.register_user(user_payload)
        user2 = service.register_user(
            {
                **user_payload,
                "document_number": generate_ecuadorian_id(),
                "email": "other@example.com",
            }
        )

        payload = {"user": user2, "new_password": "NewPassword123!"}

        with pytest.raises(
            PermissionDenied, match="You are not authorized to change this password"
        ):
            service.update_password(user1, payload)

    def test_update_password_clears_force_password_flag(self, service, user_payload):
        """Test that updating password clears force_password flag."""
        user = service.register_user(user_payload)
        user.force_password = True
        user.save()

        payload = {"user": user, "new_password": "NewPassword123!"}

        updated_user = service.update_password(user, payload)

        assert updated_user.force_password is False

    def test_update_password_without_user_in_payload(self, service, user_payload):
        """Test password update without specifying user in payload."""
        user = service.register_user(user_payload)

        payload = {"new_password": "NewPassword123!"}

        # Should use request_user as target
        updated_user = service.update_password(user, payload)
        assert updated_user is not None

    def test_update_password_invalid_payload(self, service, user_payload):
        """Test password update with an invalid payload."""
        user = service.register_user(user_payload)

        payload = {
            "user": user,
            "new_password": "123",
        }

        with pytest.raises(Exception):  # ValidationError expected
            service.update_password(user, payload)

    # --- reset_password tests ---

    def test_reset_password_success(self, service, user_payload):
        """Test successful password reset."""
        user = service.register_user(user_payload)
        old_password_hash = user.password
        new_password = "ResetPass123!"

        updated_user = service.reset_password(user, new_password)

        assert updated_user.password != old_password_hash
        assert updated_user.force_password is True
        assert updated_user.check_password(new_password) is True

    def test_reset_password_clears_lock_status(self, service, user_payload):
        """Test that password reset clears lock status."""
        user = service.register_user(user_payload)
        user.status = User.Status.LOCKED
        user.locked_at = "2024-01-01"
        user.failed_login_attempts = 5
        user.save()

        updated_user = service.reset_password(user, "NewResetPass123!")

        assert updated_user.status == User.Status.ENABLED
        assert updated_user.is_active is True
        assert updated_user.locked_at is None
        assert updated_user.failed_login_attempts == 0

    def test_reset_password_with_weak_password(self, service, user_payload):
        """Test password reset with a weak password."""
        user = service.register_user(user_payload)

        with pytest.raises(Exception):  # ValidationError expected
            service.reset_password(user, "123")

    # --- Integration tests ---

    def test_full_user_lifecycle(self, service, user_payload):
        """Test complete user lifecycle: create, update, disable, enable, reset password."""
        # Create user
        user = service.register_user(user_payload)
        assert user.status == User.Status.ENABLED

        # Update user
        update_payload = {
            "first_name": "Jane",
            "last_name": "test",
            "document_number": "2222222222",
            "phone": "+593999999999",
        }
        person = service.update_user(user, update_payload)
        assert person.first_name == "Jane"

        # Disable user
        user = service.update_status(user)
        assert user.status == User.Status.DISABLED

        # Enable user
        user = service.update_status(user)
        assert user.status == User.Status.ENABLED

        # Reset password
        new_password = "NewLifecyclePass123!"
        user = service.reset_password(user, new_password)
        assert user.check_password(new_password) is True
        assert user.force_password is True

    def test_user_with_multiple_groups(self, service, user_payload, admin_group, specialist_group):
        """Test user with multiple group assignments."""
        user_payload["groups"] = ["administrator", "specialist"]
        user = service.register_user(user_payload)

        assert user.groups.count() == 2
        assert user.groups.filter(name="administrator").exists()
        assert user.groups.filter(name="specialist").exists()

    @patch("apps.security.layers.applications.user_service.logger")
    def test_logging_on_error(self, mock_logger, service, user_payload):
        """Test that errors are properly logged."""
        # Force an error by passing invalid data
        with pytest.raises(Exception):
            service.register_user({})

        assert mock_logger.error.called
