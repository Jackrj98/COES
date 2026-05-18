from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class IndexView(LoginRequiredMixin, TemplateView):
    template_name = "layouts/base.html"
    extra_context = {"title": "Home"}
