from django.core.exceptions import PermissionDenied

GROUPS = {
    "admin": "administrator",
    "specialist": "specialist",
}


class SecurityService:
    @staticmethod
    def is_admin(user):
        """Check if the user is an administrator."""
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        return user.groups.filter(name=GROUPS["admin"]).exists()

    @staticmethod
    def is_specialist(user):
        """Check if the user belongs to a specialist group."""
        if not user or not user.is_authenticated:
            return False
        return user.groups.filter(name=GROUPS["specialist"]).exists()

    @staticmethod
    def has_access(user):
        """Check if the user has access (admin or specialist)."""
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        return user.groups.filter(name__in=[GROUPS["admin"], GROUPS["specialist"]]).exists()

    @staticmethod
    def require_admin(user, raise_exception=True):
        """Validate that the user is an administrator."""
        if not user or not user.is_authenticated:
            return False

        if not SecurityService.is_admin(user):
            if raise_exception:
                raise PermissionDenied("You need administrator privileges")
            return False
        return True

    @staticmethod
    def require_specialist(user, raise_exception=True):
        """Validate that the user belongs to a specialist group."""
        if not user or not user.is_authenticated:
            return False

        if not SecurityService.is_specialist(user):
            if raise_exception:
                raise PermissionDenied("You need specialist privileges")
            return False
        return True

    @staticmethod
    def require_access(user, raise_exception=True):
        """Validate that the user has access (admin or specialist)."""
        if not user or not user.is_authenticated:
            return False

        if not SecurityService.has_access(user):
            if raise_exception:
                raise PermissionDenied("You don't have permission to access this resource")
            return False
        return True
