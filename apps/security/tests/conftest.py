import uuid

import pytest
from django.contrib.auth.models import Group, Permission
from django.db.models import Q

from apps.security.models import Person, User
from apps.security.permissions import (
    ROLES,
)
from apps.security.utils.utils import generate_ecuadorian_id


@pytest.fixture(scope="session", autouse=True)
def setup_permissions_for_tests(django_db_setup, django_db_blocker):
    """Sincroniza permisos manualmente usando la constante ROLES.
    'django_db_setup' asegura que la BD de test esté lista.
    'django_db_blocker' permite acceder a la BD en un fixture de sesión.
    """
    print("\n--- Sincronizando permisos manualmente para los tests ---")

    with django_db_blocker.unblock():
        for role_key, role_data in ROLES.items():
            group_name = str(role_data.get("name"))
            if not group_name:
                continue

            group, created = Group.objects.get_or_create(name=group_name)

            # Construir query de permisos como en sync_roles_and_permissions
            permissions_dict = role_data.get("permissions", {})
            permission_query = Q()

            for app_label, section in permissions_dict.items():
                detail_codenames = section.get("details", [])
                model_names = section.get("models", [])

                app_q = Q(content_type__app_label=app_label)

                if detail_codenames:
                    permission_query |= app_q & Q(codename__in=detail_codenames)
                if model_names:
                    permission_query |= app_q & Q(content_type__model__in=model_names)

            matched_permissions = Permission.objects.filter(permission_query).distinct()
            group.permissions.set(matched_permissions)

            print(f"  - Grupo '{group_name}': {matched_permissions.count()} permisos asignados")

    print("--- Sincronización finalizada ---\n")


@pytest.fixture
def user_factory():
    """Factory fixture to create users with custom attributes."""

    def _create_user(force_password=False, groups=None, is_superuser=False):
        """Create a user with custom attributes."""
        uid = uuid.uuid4().hex[:8]
        username = f"user_{uid}"
        email = f"test_{uid}@example.com"
        password = "Password123!"

        person = Person.objects.create(
            first_name="Test",
            last_name="User",
            document_number=generate_ecuadorian_id(),
            phone="+593987654321",
        )

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            force_password=force_password,
            is_active=True,
            status=User.Status.ENABLED,
            person=person,
        )

        if groups:
            for group_name in groups:
                group, _ = Group.objects.get_or_create(name=group_name)
                user.groups.add(group)

        if is_superuser:
            user.is_superuser = True
            user.is_staff = True
            user.save()

        user.refresh_from_db()

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
