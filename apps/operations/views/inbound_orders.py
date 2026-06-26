import logging

from django.contrib import messages
from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View

from apps.catalogs.layers.applications import CatalogItemAppService
from apps.core.views.base import (
    CustomCreateView,
    CustomDetailView,
    CustomListView,
    CustomUpdateView,
)
from apps.operations.forms import (
    InboundOrderDetailFormSet,
    InboundOrderFilterForm,
    InboundOrderForm,
)
from apps.operations.layers.applications import InboundOrderService
from apps.operations.models import InboundOrder, OrderDetail

logger = logging.getLogger(__name__)

DEFAULT_MODEL = InboundOrder
BASE_APPS_URL = "operations:inbound"
DEFAULT_LIST_URL = reverse_lazy("operations:inbound:list")


class InboundOrdersListView(CustomListView):
    model = DEFAULT_MODEL
    success_url: str = DEFAULT_LIST_URL
    form_class = InboundOrderFilterForm
    template_name = "inbound/datatable.html"
    permission_required = "operations.view_inbound_orders"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["object"] = self.model
        ctx["description"] = _("Management of inbound orders")
        if self.model.IsActiveChoices:
            ctx["status_choices"] = self.model.StatusType.get_ui_map()

        if self.model.IsActiveColorChoices:
            ctx["status_color_choices"] = self.model.StatusType.choices
        return ctx

    def retrieve_data(self, params):
        return InboundOrderService().get_inbound_orders(params)

    def get_success_url(self):
        return self.success_url

    def get_actions(self):
        return {
            "menu_actions": {
                "title": _("Actionable"),
                "actions": [
                    {
                        "title": _("Register entry"),
                        "icon": "bi bi-plus-lg",
                        "url": reverse_lazy("operations:inbound:create"),
                    }
                ],
            }
        }


class InboundOrdersDetailView(CustomDetailView):
    app_name = "inbound"
    model = DEFAULT_MODEL
    success_url: str = DEFAULT_LIST_URL
    template_name = "inbound/detail.html"
    permission_required = "operations.view_inboundorder"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("supplier")
            .prefetch_related(
                Prefetch(
                    "details",
                    queryset=OrderDetail.objects.filter(deleted_at__isnull=True).select_related(
                        "supply", "batch"
                    ),
                )
            )
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = _("Purchase Order Details")
        object_details = self.object.details.filter(deleted_at__isnull=True)
        ctx["items"] = object_details.count()
        ctx["details"] = object_details
        return ctx

    def get_success_url(self):
        return self.success_url

    def _build_base_actions(self):
        actions_list = super()._build_base_actions()
        app_label = self.model._meta.app_label

        if self.object.status in [self.model.StatusType.DRAFT, self.model.StatusType.SENT]:
            actions_list.append(
                self.get_actions_map(
                    title=_("Mark as completed"),
                    order=3,
                    action="mark_completed",
                    icon="bi bi-check-lg",
                    url_name=f"{app_label}:{self.app_name}:completed",
                    perm=f"{app_label}.change_{self.model._meta.model_name}",
                )
            )

        if self.object.status != self.model.StatusType.CANCELLED:
            actions_list.append(
                self.get_actions_map(
                    title=_("Cancel order"),
                    order=4,
                    action="cancel",
                    icon="bi bi-x-circle",
                    url_name=f"{app_label}:{self.app_name}:cancelled",
                    perm=f"{app_label}.delete_{self.model._meta.model_name}",
                )
            )

        return actions_list


class FormSetMixin:
    model = DEFAULT_MODEL
    formset_class = InboundOrderDetailFormSet

    def get_formset(self, data=None):
        return self.formset_class(
            data=data,
            prefix="movements",
            #  queryset=OrderDetail.objects.none(),
            form_kwargs={"order_type": self.model.OrderType.INBOUND},
            # extra=1
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        data = self.request.POST if self.request.method == "POST" else None
        ctx["formset"] = self.get_formset(data)
        ctx["inbound_list"] = CatalogItemAppService().retrieve_catalog_items("CONCEPT_IN")
        return ctx

    @staticmethod
    def _clean_formset(formset):
        details_data = []
        for item in formset.cleaned_data:
            if item.get("DELETE") or not item.get("supply"):
                continue

            details_data.append(
                {
                    "supply_id": item["supply"].id,
                    "batch_number": item["batch_number"],
                    "expiry_date": item["expiry_date"],
                    "quantity_requested": item.get("quantity_requested", 0),
                    "quantity_fulfilled": item.get("quantity_fulfilled") or 0,
                    "unit_cost": item.get("unit_cost") or 0.00,
                    "observation": item.get("observations", ""),
                }
            )
        return details_data


class InboundOrderCreateView(FormSetMixin, CustomCreateView):
    model = DEFAULT_MODEL
    form_class = InboundOrderForm
    success_url: str = DEFAULT_LIST_URL
    template_name = "inbound/create_or_update.html"
    permission_required = "operations.add_inboundorder"

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        formset = self.get_formset(request.POST)

        if form.is_valid() and formset.is_valid():
            return self.form_valid(form, formset)
        return self.form_invalid(form, formset)

    def form_valid(self, form, formset):  # noqa
        details = self._clean_formset(formset)
        inbound_data = {**form.cleaned_data, "supplier": form.cleaned_data["supplier"].pk}

        try:
            with transaction.atomic():
                InboundOrderService().save_inbound_order(
                    instance=self.model(),
                    payload=inbound_data,
                    line_details=details,
                    user=self.request.user,
                )
                self._add_success_message()
            return redirect(self.success_url)
        except Exception as e:
            logger.exception("Error creating inbound order")
            return self.handle_error(str(e), e)

    def form_invalid(self, form, formset=None):
        messages.warning(self.request, self.failure_message)
        return self.render_to_response(self.get_context_data(form=form, formset=formset))

    def _add_success_message(self):
        msg = self.success_message.format(model=self.model._meta.verbose_name)
        messages.success(self.request, msg, extra_tags="toast")


class InboundOrderUpdateView(FormSetMixin, CustomUpdateView):
    model = DEFAULT_MODEL
    form_class = InboundOrderForm
    second_form_class = InboundOrderDetailFormSet
    success_url: str = DEFAULT_LIST_URL
    permission_required = "operations.change_inboundorder"
    template_name = "inbound/create_or_update.html"

    def get_formset(self, data=None):
        queryset = (
            self.object.details.select_related("batch").all()
            if self.object
            else OrderDetail.objects.none()
        )
        self.formset_class.extra = 0 if (self.object or data) else 1
        formset = self.formset_class(
            data=data,
            prefix="movements",
            queryset=queryset,
            instance=self.object,
            form_kwargs={"order_type": self.model.OrderType.INBOUND},
        )

        if not data:
            for form in formset.forms:
                if form.instance.pk and form.instance.batch:
                    form.initial["batch_number"] = form.instance.batch.batch_number
                    form.initial["expiry_date"] = form.instance.batch.expiry_date.strftime(
                        "%Y-%m-%d"
                    )
                    form.initial["supply"] = form.instance.supply.pk

        return formset

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        formset = self.get_formset(request.POST)

        if form.is_valid() and formset.is_valid():
            return self.form_valid(form, formset=formset)
        return self.form_invalid(form, formset=formset)

    def form_invalid(self, form, **kwargs):
        formset = kwargs.pop("formset", None)
        messages.warning(self.request, self.failure_message)
        return self.render_to_response(self.get_context_data(form=form, formset=formset))

    def form_valid(self, form, **kwargs):
        order_data = form.cleaned_data
        formset = kwargs.pop("formset", None)
        details = self._clean_formset(formset)
        try:
            with transaction.atomic():
                order = InboundOrderService().update_inbound_order(
                    inventory_order=self.object, payload=order_data, details_payload=details
                )

                msg_success = self.success_message.format(
                    model=self.model._meta.verbose_name, instance=order.order_number
                )
                messages.success(self.request, msg_success, extra_tags="toast")
                return redirect(order.get_absolute_url())

        except Exception as e:
            logger.error(f"Error updating purchase order: {e}", exc_info=True)
            return self.handle_error(str(e), e)


class InboundOrderMarkCompletedView(View):
    def post(self, request, external_id):
        service = InboundOrderService()
        order = get_object_or_404(InboundOrder, external_id=external_id)

        if order.status == InboundOrder.StatusType.COMPLETED:
            messages.warning(request, _("Order already completed."))
            return redirect(order.get_absolute_url())

        try:
            service.complete_purchase_order(order)
            messages.success(request, _("Order completed successfully."))
        except Exception as e:
            logger.error(_(f"Error completing order: {e}"))
            messages.error(request, _("Failed to complete order."))

        return redirect(order.get_absolute_url())


class InboundOrderMarkCancelView(View):
    def post(self, request, external_id):
        service = InboundOrderService()
        order = get_object_or_404(InboundOrder, external_id=external_id)

        try:
            service.cancel_purchase_order(order)
            messages.success(request, _("Order cancel successfully."))
        except Exception as e:
            logger.error(_(f"Error cancel order: {e}"))
            messages.error(request, _("Failed to cancel order."))

        return redirect(order.get_absolute_url())
