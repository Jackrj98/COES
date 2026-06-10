from django.core.exceptions import PermissionDenied

from apps.security.permissions import ALL_GROUP_NAMES, GROUP_NAMES


class SecurityService:
    @staticmethod
    def is_admin(user):
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return user.groups.filter(name=GROUP_NAMES["administrator"]).exists()

    @staticmethod
    def is_specialist(user):
        if not user or not user.is_authenticated:
            return False
        return user.groups.filter(name=GROUP_NAMES["specialist"]).exists()

    @staticmethod
    def has_access(user):
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return user.groups.filter(name__in=ALL_GROUP_NAMES).exists()

    @staticmethod
    def _handle_failure(user, message, raise_exception):
        if not user or not user.is_authenticated:
            return False

        if raise_exception:
            raise PermissionDenied(message)
        return False

    @staticmethod
    def require_admin(user, raise_exception=True):
        if SecurityService.is_admin(user):
            return True
        return SecurityService._handle_failure(
            user, "You need administrator privileges", raise_exception
        )

    @staticmethod
    def require_specialist(user, raise_exception=True):
        if SecurityService.is_specialist(user):
            return True
        return SecurityService._handle_failure(
            user, "You need specialist privileges", raise_exception
        )

    @staticmethod
    def require_access(user, raise_exception=True):
        if SecurityService.has_access(user):
            return True
        return SecurityService._handle_failure(
            user, "You don't have permission to access this resource", raise_exception
        )
