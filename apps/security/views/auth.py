from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

from apps.security.forms.auth import SignInForm
from apps.security.models import User
from apps.security.utils.constants import MessagesEnum


class SignInView(LoginView):
    model = User
    form_class = SignInForm
    template_name = "authentication/sign_in.html"
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
        """Handles user authentication process."""
        form = self.form_class(data=request.POST)

        identifier = request.POST.get("username")
        password = request.POST.get("password")
        try:
            user = User.objects.get_by_natural_key(identifier)
        except User.DoesNotExist:
            messages.warning(request, MessagesEnum.INVALID_CREDENTIALS.value, extra_tags="toast")
            return self.render_to_response(self.get_context_data(form=form))

        if not user.is_active:
            messages.warning(request, MessagesEnum.USER_INACTIVE.value, extra_tags="toast")
            return self.render_to_response(self.get_context_data(form=form))

        auth_user = authenticate(request, username=user.email, password=password)
        if auth_user:
            login(request, auth_user)
            return self.handle_login_success(user)

        if user.is_locked:
            messages.warning(request, MessagesEnum.USER_BLOCKED.value, extra_tags="toast")

        attempts = int(5 - user.failed_login_attempts)
        messages.warning(
            request,
            MessagesEnum.INVALID_CREDENTIALS_WITH_ATTEMPTS.value.format(number=attempts),
            extra_tags="toast",
        )
        return self.render_to_response(self.get_context_data(form=form))

    def handle_login_success(self, user):
        initials = "US"
        session_name = user.username
        person = getattr(user, "person", None)

        if person:
            initials = getattr(person, "initials", "NN")
            session_name = getattr(person, "session_name", "NN")

        self.request.session["initials"] = initials
        self.request.session["session_name"] = session_name

        if getattr(user, "force_password", False):
            messages.warning(self.request, MessagesEnum.FORCED_PASSWORD.value, extra_tags="toast")
            return redirect("users:password_change")

        return redirect(self.get_success_url())


class SignOutView(LogoutView):
    http_method_names = ["post"]
    next_page = settings.LOGOUT_REDIRECT_URL
