import logging

from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from apps.catalogs.layers.applications import CatalogItemAppService
from apps.core.views.base import (
    CustomCreateView,
    CustomDetailView,
    CustomListView,
)
from apps.operations.forms import OutboundOrderDetailFormSet, OutboundOrderForm
from apps.operations.layers.applications import (
    OutboundOrderService,
)
from apps.operations.models import OrderDetail, OutboundOrder

logger = logging.getLogger(__name__)

DEFAULT_MODEL = OutboundOrder
DEFAULT_LIST_URL = reverse_lazy("operations:outbound:list")


class OutboundOrderListView(CustomListView):
    model = DEFAULT_MODEL
    success_url: str = DEFAULT_LIST_URL
    template_name = "outbound/datatable.html"
    permission_required = "operations.view_outbound_orders"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["object"] = self.model
        ctx["description"] = _("Management of outbound orders")
        if self.model.IsActiveChoices:
            ctx["status_choices"] = self.model.StatusType.get_ui_map()

        if self.model.IsActiveColorChoices:
            ctx["status_color_choices"] = self.model.StatusType.choices

        return ctx

    def retrieve_data(self, params):
        return OutboundOrderService().get_outbound_orders(params)

    def get_success_url(self):
        return self.success_url

    def get_actions(self):
        return {
            "menu_actions": {
                "title": _("Actionable"),
                "actions": [
                    {
                        "title": _("Register outbound"),
                        "icon": "bi bi-plus-lg",
                        "url": reverse_lazy("operations:outbound:create"),
                    }
                ],
            }
        }


class OutboundOrderDetailView(CustomDetailView):
    app_name = "outbound"
    model = DEFAULT_MODEL
    success_url: str = DEFAULT_LIST_URL
    template_name = "outbound/detail.html"
    permission_required = "operations.view_outboundorder"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = _("Exit Order Details")
        object_details = self.object.details.filter(deleted_at__isnull=True)
        ctx["items"] = object_details.count()
        ctx["details"] = object_details
        return ctx

    def get_success_url(self):
        return self.success_url


class OutboundOrderCreateView(CustomCreateView):
    model = DEFAULT_MODEL
    form_class = OutboundOrderForm
    second_form_class = OutboundOrderDetailFormSet
    success_url: str = DEFAULT_LIST_URL
    template_name = "outbound/create_or_update.html"
    permission_required = "operations.add_outboundorder"

    def get_formset(self):
        if self.request.method == "POST":
            return self.second_form_class(
                self.request.POST, prefix="movements", queryset=OrderDetail.objects.none()
            )
        else:
            return self.second_form_class(prefix="movements", queryset=OrderDetail.objects.none())

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["formset"] = self.get_formset()
        ctx["supply_search_url"] = reverse_lazy("inventory:supplies:search")
        ctx["outbound_list"] = CatalogItemAppService().retrieve_catalog_items("CONCEPT_OUT")
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
        order_service = OutboundOrderService()
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
                        "observation": item.get("observation", ""),
                    }
                )
            order_service.save_outbound_order(
                self.model(), form.cleaned_data, details_data, self.request.user
            )

            # Show success message
            model_name = self.model._meta.verbose_name
            msg_success = self.success_message.format(model=model_name)
            messages.success(self.request, msg_success, extra_tags="toast")
            return redirect(self.success_url)

        except Exception as e:
            return self.handle_error(str(e), e)
