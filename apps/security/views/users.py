from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import CreateView

from apps.security.models import Person, User

DEFAULT_MODEL = User
DEFAULT_SECOND_MODEL = Person


class UserCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = DEFAULT_MODEL
    second_model = DEFAULT_MODEL
    form_class = []
    template_name = "users/create_or_update.html"
    permission_required = ["security.add_user"]
