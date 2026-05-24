from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

from apps.security.forms.auth import SignInForm
from apps.security.layers.builders import SessionBuilder
from apps.security.models import User
from apps.security.utils.constants import MessagesEnum


class SignInView(LoginView):
    model = User
    form_class = SignInForm
    template_name = "auth/sign_in.html"
    success_url = settings.LOGIN_REDIRECT_URL
    extra_context = {
        "title": _("Sign In"),
        "description": _("Log in to your account"),
    }

    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(self.success_url)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """Handles the user authentication process."""
        form = self.form_class(data=request.POST)
        password = request.POST.get("password")
        identifier = request.POST.get("username")
        try:
            user = User.objects.get_by_natural_key(identifier)
        except User.DoesNotExist:
            messages.warning(request, MessagesEnum.INVALID_CREDENTIALS.value, extra_tags="toast")
            return self.render_to_response(self.get_context_data(form=form))

        remaining_attempts = 5 - (user.failed_login_attempts + 1)
        if user.status == self.model.Status.LOCKED or remaining_attempts == 0:
            messages.warning(request, MessagesEnum.USER_BLOCKED.value, extra_tags="toast")
            return self.render_to_response(self.get_context_data(form=form))

        if not user.is_active:
            messages.warning(request, MessagesEnum.USER_INACTIVE.value, extra_tags="toast")
            return self.render_to_response(self.get_context_data(form=form))

        auth_user = authenticate(request, username=user.email, password=password)
        if auth_user:
            login(request, auth_user)
            return self.handle_login_success(auth_user)

        messages.warning(
            request,
            MessagesEnum.INVALID_CREDENTIALS_WITH_ATTEMPTS.value.format(number=remaining_attempts),
            extra_tags="toast",
        )
        return self.render_to_response(self.get_context_data(form=form))

    def handle_login_success(self, user):
        builder = SessionBuilder(user, self.request)

        next_url = (
            builder.build_initials()
            .build_group_name()
            .build_session_name()
            .check_forced_password()
            .build()
        )
        if next_url:
            messages.warning(self.request, MessagesEnum.FORCED_PASSWORD.value, extra_tags="toast")

            return redirect(reverse(next_url, kwargs={"external_id": user.external_id}))

        return redirect(self.get_success_url())


class SignOutView(LogoutView):
    http_method_names = ["post"]
    next_page = settings.LOGOUT_REDIRECT_URL
