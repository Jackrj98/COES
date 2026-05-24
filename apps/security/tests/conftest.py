import uuid

import pytest
from django.contrib.auth.models import Group, Permission
from django.db.models import Q

from apps.core.utils.permissions import Permissions
from apps.security.layers.applications.user_service import UserAppService
from apps.security.models import User
from apps.security.utils.utils import generate_ecuadorian_id


@pytest.fixture(scope="session", autouse=True)
def setup_permissions_for_tests(django_db_setup, django_db_blocker):
    """Sincroniza permisos manualmente.
    'django_db_setup' asegura que la BD de test esté lista.
    'django_db_blocker' permite acceder a la BD en un fixture de sesión.
    """
    print("\n--- Sincronizando permisos manualmente para los tests ---")

    with django_db_blocker.unblock():  # <-- ESTO es lo que permite el acceso en scope='session'
        for group_data in Permissions.groups_permissions:
            group_name = str(group_data.get("name"))
            group, _ = Group.objects.get_or_create(name=group_name)

            permissions = group_data.get("permissions", {})
            permission_query = Q()

            for app_name, app_permissions in permissions.items():
                detail_permissions = app_permissions.get("details", [])
                app_query = Q(content_type__app_label=app_name)
                detail_query = Q(codename__in=detail_permissions)
                permission_query |= app_query & detail_query

            matched_permissions = Permission.objects.filter(permission_query)
            group.permissions.set(matched_permissions)

    print("--- Sincronización finalizada ---\n")


@pytest.fixture
def user_factory():
    """Factory fixture to create users with custom attributes."""

    def _create_user(force_password=False, groups=None, is_superuser=False):
        """Create a user with custom attributes.

        Args:
            force_password (bool): Whether the user must change the password on next login
            groups (list): List of group names to assign to the user.
            is_superuser (bool): Whether to grant superuser privileges

        Returns:
            User: Created user instance
        """
        service = UserAppService()
        uid = uuid.uuid4().hex[:8]

        # Build user payload with default test data
        payload = {
            "username": f"user_{uid}",
            "email": f"test_{uid}@example.com",
            "password": "Password123!",
            "first_name": "Test",
            "last_name": "User",
            "document_number": generate_ecuadorian_id(),
            "phone": "+593987654321",
            "groups": groups or [],  # Ensure groups is always a list
        }

        # Register user through the application service
        user = service.register_user(payload)
        user.force_password = force_password

        # Set superuser flags if requested
        if is_superuser:
            user.is_superuser = True
            user.is_staff = True

        user.save()
        return user

    return _create_user


@pytest.fixture
def admin_user(db):
    """Create a superuser admin for testing without authentication."""
    from apps.security.models import User

    return User.objects.create_superuser("admin", "admin@test.com", "password")


@pytest.fixture
def user_with_perms(db):
    """Create a regular user with specific permissions.

    Permissions granted:
        - add_user, add_person (create)
        - change_user (update)
        - view_user, view_person (read)
    """
    user = User.objects.create_user(
        username="testenv", email="test@example.com", password="Password123!"
    )

    # Filter and assign specific permissions
    perms = Permission.objects.filter(
        codename__in=["add_user", "add_person", "change_user", "view_user", "view_person"]
    )
    user.user_permissions.set(perms)
    return user


@pytest.fixture
def admin_client(client, user_factory):
    """Authenticated client with admin/superuser privileges.

    Returns:
        tuple: (client, user) where the user is an authenticated admin
    """
    user = user_factory(is_superuser=True, groups=["administrator"])
    client.force_login(user)
    return client, user


@pytest.fixture
def specialist_client(client, user_factory, force_password=False):
    """Authenticated client with a specialist role.

    Args:
        client (TestClient): Django test client
        user_factory (function): Factory function to create users
        force_password (bool): Whether the user must change the password on the next login

    Returns:
        tuple: (client, user) where the user is an authenticated specialist
    """
    user = user_factory(groups=["specialist"], force_password=force_password)
    user.refresh_from_db()

    if hasattr(user, "_perm_cache"):
        del user._perm_cache

    print(f"DEBUG: Grupos: {user.groups.all()}")
    print(f"DEBUG: Permisos: {user.get_all_permissions()}")

    grupo = user.groups.first()
    print(f"DEBUG: Nombre del grupo: {grupo.name}")
    print(
        f"DEBUG: Permisos en el grupo: {list(grupo.permissions.all().values_list('codename', flat=True))}"
    )

    client.force_login(user)
    return client, user


@pytest.fixture
def admin_user_unauthenticated(user_factory):
    """Returns an admin user WITHOUT authentication.
    Useful for testing login functionality (not pre-authenticated).

    Returns:
        User: Unauthenticated admin user instance
    """
    return user_factory(is_superuser=True, groups=["administrator"])


@pytest.fixture
def specialist_user_unauthenticated(user_factory):
    """Returns a specialist user WITHOUT authentication.
    Useful for testing login functionality (not pre-authenticated).

    Returns:
        User: Unauthenticated specialist user instance
    """
    return user_factory(groups=["specialist"])
