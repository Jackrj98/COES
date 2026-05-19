from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver
from django.utils import timezone

User = get_user_model()


@receiver(user_login_failed)
def login_failed_handler(sender, credentials, **kwargs):
    username = credentials.get("username")
    try:
        user = User.objects.get(username=username)

        if user.is_locked:
            return

        user.failed_login_attempts += 1

        if user.failed_login_attempts >= 5:
            user.is_locked = True
            user.is_active = False
            user.locked_at = timezone.now()

        user.save()
    except User.DoesNotExist:
        pass


@receiver(user_logged_in)
def login_success_handler(sender, user, **kwargs):
    if user.failed_login_attempts > 0:
        user.failed_login_attempts = 0
        user.is_locked = False
        user.locked_at = None
        user.save()
