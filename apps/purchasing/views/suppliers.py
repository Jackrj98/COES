import logging

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from pydantic import ValidationError

from apps.core.views.base import (
    CustomCreateView,
    CustomDetailView,
    CustomListView,
    CustomStatusUpdateView,
    CustomUpdateView,
)
from apps.purchasing.forms import SupplierBaseForm, SupplierFilterForm
from apps.purchasing.layers.applications import SupplierAppService
from apps.purchasing.models import Supplier
from apps.security.layers.security import SecurityService

logger = logging.getLogger(__name__)

DEFAULT_MODEL = Supplier
DEFAULT_LIST_URL = reverse_lazy("purchasing:suppliers:list")


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class SupplierListView(CustomListView):
    model = DEFAULT_MODEL
    form_class = SupplierFilterForm
    success_url: str = DEFAULT_LIST_URL
    template_name = "suppliers/datatable.html"
    permission_required = "purchasing.view_supplier"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["object"] = self.model
        ctx["description"] = _("Management of registered suppliers")

        # Delivery time statistics
        suppliers = self.object_list

        # Count suppliers by delivery time
        fast_delivery = suppliers.filter(delivery_days__lte=5).count()  # 1-5 days
        medium_delivery = suppliers.filter(delivery_days__range=(6, 14)).count()  # 6-14 days
        slow_delivery = suppliers.filter(delivery_days__gte=15).count()  # 15+ days

        ctx["fast_delivery"] = fast_delivery
        ctx["medium_delivery"] = medium_delivery
        ctx["slow_delivery"] = slow_delivery
        ctx["total_suppliers"] = suppliers.filter(deleted_at__isnull=True).count()

        # Optional: Add percentages
        total = ctx["total_suppliers"]
        if total > 0:
            ctx["fast_percentage"] = round((fast_delivery / total) * 100, 1)
            ctx["medium_percentage"] = round((medium_delivery / total) * 100, 1)
            ctx["slow_percentage"] = round((slow_delivery / total) * 100, 1)
        else:
            ctx["fast_percentage"] = 0
            ctx["medium_percentage"] = 0
            ctx["slow_percentage"] = 0

        return ctx

    def retrieve_data(self, params):
        return SupplierAppService().retrieve_suppliers(params)

    def get_success_url(self):
        return self.success_url


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class SupplierDetailView(CustomDetailView):
    app_name = "suppliers"
    model = DEFAULT_MODEL
    success_url: str = DEFAULT_LIST_URL
    template_name = "suppliers/detail.html"
    permission_required = "purchasing.view_supplier"

    def get_object(self, queryset=None):
        """Cache the object to avoid duplicate queries."""
        if not hasattr(self, "_cached_object"):
            self._cached_object = super().get_object(queryset)
        return self._cached_object

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["is_admin"] = SecurityService.is_admin(self.request.user)
        ctx["title"] = _("Supplier Details")

        return ctx

    def get_success_url(self):
        return self.success_url


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class SupplierCreateView(CustomCreateView):
    model = DEFAULT_MODEL
    form_class = SupplierBaseForm
    success_url: str = DEFAULT_LIST_URL
    permission_required = "purchasing.add_supplier"
    template_name = "suppliers/create_or_update.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if "form" not in ctx:
            ctx["form"] = self.get_form()

        return ctx

    def post(self, request, *args, **kwargs):
        form = self.get_form()

        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form, **kwargs):
        service = SupplierAppService()

        try:
            data = form.cleaned_data
            service.register_supplier(payload={**data})
            messages.success(
                self.request,
                self.success_message.format(model=self.model._meta.verbose_name),
                extra_tags="toast",
            )
            return redirect(self.success_url)

        except ValidationError as e:
            self.handle_pydantic_error(e, form)
            return self.form_invalid(form)
        except Exception as e:
            return self.handle_error(str(e), e)

    def form_invalid(self, form):
        messages.warning(self.request, self.failure_message.value)
        return self.render_to_response(self.get_context_data(form=form))


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class SupplierUpdateView(CustomUpdateView):
    model = DEFAULT_MODEL
    form_class = SupplierBaseForm
    success_url: str = DEFAULT_LIST_URL
    permission_required = "purchasing.change_supplier"
    template_name = "suppliers/create_or_update.html"

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def get_object(self, queryset=None):
        if not hasattr(self, "_cached_object"):
            self._cached_object = super().get_object(queryset)
        return self._cached_object

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = _("Update Supplier")
        referer = self.request.META.get("HTTP_REFERER", "")

        if str(self.object.external_id) in referer:
            ctx["cancel_url"] = self.object.get_absolute_url()
        else:
            ctx["cancel_url"] = self.success_url

        if "form" not in ctx:
            ctx["form"] = self.get_form()

        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()

        if form.is_valid():
            return self.form_valid(form)

        return self.form_invalid(form)

    def form_valid(self, form):
        service = SupplierAppService()

        try:
            service.update_supplier(
                instance=self.get_object(),
                payload={**form.cleaned_data},
            )

            messages.success(
                self.request,
                self.success_message.format(
                    model=self.model._meta.verbose_name, instance=self.get_object().business_name
                ),
                extra_tags="toast",
            )
            return redirect(self.success_url)

        except ValidationError as e:
            self.handle_pydantic_error(e, form)
            return self.form_invalid(form)
        except Exception as e:
            return self.handle_error(str(e), e)

    def form_invalid(self, form):
        messages.warning(self.request, self.failure_message)
        return self.render_to_response(self.get_context_data(form=form))


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class SupplierStatusUpdateView(CustomStatusUpdateView):
    model = DEFAULT_MODEL
    success_url: str = DEFAULT_LIST_URL
    permission_required = "purchasing.change_supplier"

    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        print(instance)
        model_name = self.model._meta.verbose_name.lower()  # noqa

        return JsonResponse(
            {
                "success": True,
                "title": _("Change Status"),
                "description": _(
                    f"Are you sure you want to change the status of this {model_name}?"
                ),
                "name": instance.business_name,
                "email": instance.email,
                "is_active": instance.is_active,
            }
        )

    def post(self, request, *args, **kwargs):
        try:
            user = self.get_object()
            SupplierAppService().update_status(user)
            return JsonResponse({"success": True, "message": self.success_message})
        except Exception as e:
            logger.error(f"Error updating status: {e}", exc_info=True)
            return JsonResponse({"success": False, "message": self.failure_message}, status=500)
