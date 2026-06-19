import logging

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from apps.core.views.base import (
    CustomCreateView,
    CustomDetailView,
    CustomListView,
    CustomStatusUpdateView,
    CustomUpdateView,
)
from apps.operations.forms import SupplierBaseForm, SupplierFilterForm
from apps.operations.layers.applications import SupplierAppService
from apps.operations.models import Supplier

logger = logging.getLogger(__name__)

DEFAULT_MODEL = Supplier
DEFAULT_LIST_URL = reverse_lazy("operations:suppliers:list")


class SupplierListView(CustomListView):
    model = DEFAULT_MODEL
    form_class = SupplierFilterForm
    success_url: str = DEFAULT_LIST_URL
    template_name = "suppliers/datatable.html"
    permission_required = "operations.view_supplier"

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


class SupplierDetailView(CustomDetailView):
    app_name = "suppliers"
    model = DEFAULT_MODEL
    success_url: str = DEFAULT_LIST_URL
    template_name = "suppliers/detail.html"
    permission_required = "operations.view_supplier"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = _("Supplier Details")
        return ctx

    def get_success_url(self):
        return self.success_url


class SupplierCreateView(CustomCreateView):
    model = DEFAULT_MODEL
    form_class = SupplierBaseForm
    success_url: str = DEFAULT_LIST_URL
    permission_required = "operations.add_supplier"
    template_name = "suppliers/create_or_update.html"

    def form_valid(self, form, **kwargs):
        service = SupplierAppService()

        try:
            supplier_data = form.cleaned_data
            service.register_supplier(payload=supplier_data)

            # Show success message
            model_name = self.model._meta.verbose_name
            msg_success = self.success_message.format(model=model_name)
            messages.success(self.request, msg_success, extra_tags="toast")
            return redirect(self.success_url)

        except ValueError:
            return self.form_invalid(form)
        except Exception as e:
            return self.handle_error(str(e), e)


class SupplierUpdateView(CustomUpdateView):
    model = DEFAULT_MODEL
    form_class = SupplierBaseForm
    success_url: str = DEFAULT_LIST_URL
    permission_required = "operations.change_supplier"
    template_name = "suppliers/create_or_update.html"

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def form_valid(self, form):
        service = SupplierAppService()

        try:
            supplier_data = form.cleaned_data
            instance = service.update_supplier(instance=self.object, payload=supplier_data)

            # Show success message
            model_name = self.model._meta.verbose_name
            contact_name = instance.short_name
            msg_success = self.success_message.format(model=model_name, instance=contact_name)
            messages.success(self.request, msg_success, extra_tags="toast")
            return redirect(self.success_url)

        except Exception as e:
            return self.handle_error(str(e), e)


class SupplierStatusUpdateView(CustomStatusUpdateView):
    model = DEFAULT_MODEL
    success_url: str = DEFAULT_LIST_URL
    permission_required = "operations.change_supplier"

    def get(self, request, *args, **kwargs):
        instance = self.get_object()
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
