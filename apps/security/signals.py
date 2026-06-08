from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.utils import timezone

from ..security.permissions import sync_roles_and_permissions

User = get_user_model()


@receiver(post_migrate)
def populate_groups_permissions(sender, **kwargs):
    """Synchronize groups and permissions automatically after migrations."""
    # Only run this on the security and core apps
    if sender.label in ["security", "core"]:
        sync_roles_and_permissions(verbosity=1)


@receiver(user_login_failed)
def login_failed_handler(sender, credentials, **kwargs):
    username = credentials.get("username")
    try:
        user = User.objects.get(username=username)
        if user.status == User.Status.LOCKED:
            return

        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.status = User.Status.LOCKED
            user.is_active = False
            user.locked_at = timezone.now()

        user.save()
    except User.DoesNotExist:
        pass


@receiver(user_logged_in)
def login_success_handler(sender, user, **kwargs):
    if user.failed_login_attempts > 0:
        user.failed_login_attempts = 0
        user.status = User.Status.ENABLED
        user.locked_at = None
        user.save()
