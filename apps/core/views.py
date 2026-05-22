from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView


class IndexView(LoginRequiredMixin, TemplateView):
    template_name = "layouts/base.html"
    extra_context = {"title": "Home"}


class CustomPermissionDeniedView(TemplateView):
    template_name = "errors/403.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["exception"] = self.kwargs.get("exception")
        return context

    def get(self, request, *args, **kwargs):
        messages.error(request, _("You do not have permission to perform this action."))
        # Retornamos explícitamente el status 403 para que los tests pasen
        return self.render_to_response(self.get_context_data(**kwargs), status=403)


class CustomPageNotFoundView(TemplateView):
    template_name = "errors/404.html"

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.get_context_data(**kwargs), status=404)


class CustomServerErrorView(TemplateView):
    template_name = "errors/500.html"

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.get_context_data(**kwargs), status=500)


def handler403(request, exception=None):
    return CustomPermissionDeniedView.as_view()(request, exception=exception)


def handler404(request, exception=None):
    return CustomPageNotFoundView.as_view()(request, exception=exception)


def handler500(request):
    return CustomServerErrorView.as_view()(request)
