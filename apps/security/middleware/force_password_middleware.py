from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

from apps.security.models import User
from apps.security.utils.constants import MessagesEnum


class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)

        if not hasattr(request, "_user_cached_instance"):
            request._user_cached_instance = User.objects.select_related("person").get(
                pk=request.user.pk
            )

        user = request._user_cached_instance

        allowed_url = reverse(
            "security:users:password_change", kwargs={"external_id": user.external_id}
        )
        logout_url = reverse("security:logout")

        if getattr(user, "force_password", False):
            if request.path not in [allowed_url, logout_url]:
                messages.warning(request, MessagesEnum.FORCED_PASSWORD.value, extra_tags="toast")
                return redirect(allowed_url)

        return self.get_response(request)
