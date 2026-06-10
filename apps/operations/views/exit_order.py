import logging

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from pydantic import ValidationError

from apps.catalogs.layers.applications import CatalogItemAppService
from apps.core.views.base import (
    CustomCreateView,
    CustomDetailView,
    CustomListView,
)
from apps.operations.forms import ExitOrderBaseForm, ExitOrderDetailFormSet, ExitOrderFilterForm
from apps.operations.layers.applications import OrderAppService
from apps.operations.layers.applications.inventory_service import InventoryOrchestrator
from apps.operations.layers.dto import ExitOrderDTO
from apps.operations.models import ExitDetail, ExitOrder
from apps.security.layers.security import SecurityService

logger = logging.getLogger(__name__)

DEFAULT_MODEL = ExitOrder
DEFAULT_LIST_URL = reverse_lazy("operations:outbound_order:list")


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class ExitOrderListView(CustomListView):
    model = DEFAULT_MODEL
    form_class = ExitOrderFilterForm
    success_url: str = DEFAULT_LIST_URL
    template_name = "operations/outbound/datatable.html"
    permission_required = ["operations.view_exitorder", "operations.view_exitdetail"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["object"] = self.model
        ctx["description"] = _("Management of exit orders")
        if self.model.IsActiveChoices:
            ctx["status_choices"] = self.model.Status.choices

        if self.model.IsActiveColorChoices:
            ctx["status_color_choices"] = self.model.StatusColor.choices
        return ctx

    def retrieve_data(self, params):
        return OrderAppService.retrieve_exit_orders(params)

    def get_success_url(self):
        return self.success_url

    def get_actions(self):
        return {
            "menu_actions": {
                "title": _("Actionable"),
                "actions": [
                    {
                        "title": _("Register exit"),
                        "icon": "bi bi-plus-lg",
                        "url": reverse_lazy("operations:outbound_order:create"),
                    }
                ],
            }
        }


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class ExitOrderDetailView(CustomDetailView):
    app_name = "outbound_order"
    model = DEFAULT_MODEL
    success_url: str = DEFAULT_LIST_URL
    template_name = "operations/outbound/detail.html"
    permission_required = ["operations.view_exitorder", "operations.view_exitdetail"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = _("Exit Order Details")
        object_details = self.object.details.filter(deleted_at__isnull=True)
        ctx["items"] = object_details.count()
        ctx["details"] = object_details
        return ctx

    def get_success_url(self):
        return self.success_url


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class ExitOrderCreateView(CustomCreateView):
    model = DEFAULT_MODEL
    form_class = ExitOrderBaseForm
    second_form_class = ExitOrderDetailFormSet
    success_url: str = DEFAULT_LIST_URL
    template_name = "operations/outbound/create_or_update.html"
    permission_required = ["operations.add_exitorder", "operations.add_exitdetail"]

    def get_formset(self):
        if self.request.method == "POST":
            return self.second_form_class(
                self.request.POST, prefix="movements", queryset=ExitDetail.objects.none()
            )
        else:
            return self.second_form_class(prefix="movements", queryset=ExitDetail.objects.none())

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["formset"] = self.get_formset()
        ctx["supply_search_url"] = reverse_lazy("inventory:supplies:search")
        datalist = CatalogItemAppService().retrieve_catalog_items("CONCEPT_OUT")
        ctx["motive_list"] = datalist
        return ctx

    def post(self, request, *args, **kwargs):
        """Handle POST request."""
        self.object = None

        form = self.get_form()
        formset = self.get_formset()

        if form.is_valid() and formset.is_valid():
            return self.form_valid(form, formset=formset)
        return self.form_invalid(form, formset=formset)

    def form_invalid(self, form, **kwargs):
        formset = kwargs.pop("formset", None)
        messages.warning(self.request, self.failure_message)
        return self.render_to_response(self.get_context_data(form=form, formset=formset))

    @transaction.atomic
    def form_valid(self, form, **kwargs):
        order_service = OrderAppService()
        inventory_service = InventoryOrchestrator()
        formset = kwargs.pop("formset", None)
        try:
            details_data = []
            for item in formset.cleaned_data:
                if item.get("DELETE") or not item.get("supply"):
                    continue

                details_data.append(
                    {
                        "supply_id": item["supply"].id,
                        "quantity_requested": item["quantity_requested"],
                        "unit_cost": item.get("unit_cost", 0.00),
                        "observation": item.get("observation", ""),
                    }
                )

            order_dto = ExitOrderDTO(
                requested_by=self.request.user.email,
                observations=form.cleaned_data.get("observations", ""),
                motive=form.cleaned_data.get("motive", ""),
                status=self.model.Status.COMPLETED,
                details=details_data,
            )
            order = order_service.create_exit_order(payload=order_dto)
            inventory_service.register_exit(order=order, details_payload=order_dto.details)

            # Show success message
            model_name = self.model._meta.verbose_name
            msg_success = self.success_message.format(model=model_name)
            messages.success(self.request, msg_success, extra_tags="toast")
            return redirect(self.success_url)

        except ValidationError as e:
            self.handle_pydantic_error(e, form)
            return self.form_invalid(form, formset=formset)
        except Exception as e:
            return self.handle_error(str(e), e)
