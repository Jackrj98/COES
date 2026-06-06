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
    def require_admin(user, raise_exception=True):
        if not SecurityService.is_admin(user):
            if raise_exception:
                raise PermissionDenied("You need administrator privileges")
            return False
        return True

    @staticmethod
    def require_specialist(user, raise_exception=True):
        if not SecurityService.is_specialist(user):
            if raise_exception:
                raise PermissionDenied("You need specialist privileges")
            return False
        return True

    @staticmethod
    def require_access(user, raise_exception=True):
        if not SecurityService.has_access(user):
            if raise_exception:
                raise PermissionDenied("You don't have permission to access this resource")
            return False
        return True
