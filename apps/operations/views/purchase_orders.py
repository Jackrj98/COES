import logging

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import View
from pydantic import ValidationError

from apps.catalogs.layers.applications import CatalogItemAppService
from apps.core.views.base import (
    CustomCreateView,
    CustomDetailView,
    CustomListView,
    CustomUpdateView,
)
from apps.operations.forms import (
    PurchaseOrderBase,
    PurchaseOrderDetailFormSet,
    PurchaseOrderFilterForm,
)
from apps.operations.layers.applications import (
    PurchaseAppService,
    PurchaseOrchestrator,
)
from apps.operations.layers.dto import PurchaseOrderDTO
from apps.operations.models import PurchaseOrder, PurchaseOrderDetail
from apps.security.layers.security import SecurityService

logger = logging.getLogger(__name__)

DEFAULT_MODEL = PurchaseOrder
BASE_APPS_URL = "operations:inbound_order"
DEFAULT_LIST_URL = reverse_lazy("operations:inbound_order:list")


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class PurchaseOrderListView(CustomListView):
    model = DEFAULT_MODEL
    success_url: str = DEFAULT_LIST_URL
    form_class = PurchaseOrderFilterForm
    template_name = "operations/inbound/datatable.html"
    permission_required = ["operations.view_purchaseorder", "operations.view_purchasedetail"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["object"] = self.model
        ctx["description"] = _("Management of purchase orders")
        if self.model.IsActiveChoices:
            ctx["status_choices"] = self.model.Status.get_ui_map()

        if self.model.IsActiveColorChoices:
            ctx["status_color_choices"] = self.model.Status.choices
        return ctx

    def retrieve_data(self, params):
        return PurchaseAppService().retrieve_purchase_orders(params)

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
                        "url": reverse_lazy("operations:inbound_order:create"),
                    }
                ],
            }
        }


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class PurchaseOrderDetailView(CustomDetailView):
    app_name = "inbound_order"
    model = DEFAULT_MODEL
    success_url: str = DEFAULT_LIST_URL
    template_name = "operations/inbound/detail.html"
    permission_required = ["operations.view_purchaseorder", "operations.view_purchasedetail"]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("supplier")
            .prefetch_related(
                Prefetch(
                    "details",
                    queryset=PurchaseOrderDetail.objects.filter(
                        deleted_at__isnull=True
                    ).select_related("supply", "batch"),
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

        if self.object.status in [self.model.Status.DRAFT, self.model.Status.SENT]:
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

        if self.object.status != self.model.Status.CANCELLED:
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


class PurchaseFormSetMixin:
    second_form_class = PurchaseOrderDetailFormSet

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["formset"] = self.get_formset()
        ctx["supply_search_url"] = reverse_lazy("inventory:supplies:search")
        ctx["purchase_list"] = CatalogItemAppService().retrieve_catalog_items("CONCEPT_IN")
        return ctx

    @staticmethod
    def _prepare_order(data, details_data):
        return PurchaseOrderDTO(
            status=data["status"],
            motive=data["motive"],
            observations=data["observations"],
            estimated_delivery=data["estimated_delivery"],
            actual_delivery=data["actual_delivery"],
            supplier_id=data["supplier"].id,
            details=details_data,
        )

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
                    "quantity_requested": item["quantity_requested"],
                    "quantity_received": item["quantity_received"],
                    "unit_cost": item.get("unit_cost", 0.00),
                    "observation": item.get("observation", ""),
                }
            )
        return details_data


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class PurchaseOrderCreateView(PurchaseFormSetMixin, CustomCreateView):
    model = DEFAULT_MODEL
    form_class = PurchaseOrderBase
    second_form_class = PurchaseOrderDetailFormSet
    success_url: str = DEFAULT_LIST_URL
    permission_required = ["operations.add_purchaseorder"]
    template_name = "operations/inbound/create_or_update.html"

    def get_formset(self):
        if self.request.method == "POST":
            return self.second_form_class(
                self.request.POST, prefix="movements", queryset=PurchaseOrderDetail.objects.none()
            )

        else:
            return self.second_form_class(
                prefix="movements", queryset=PurchaseOrderDetail.objects.none()
            )

    def post(self, request, *args, **kwargs):
        self.object = None  # noqa
        form, formset = self.get_form(), self.get_formset()
        if form.is_valid() and formset.is_valid():
            return self.form_valid(form, formset=formset)
        return self.form_invalid(form, formset=formset)

    def form_invalid(self, form, **kwargs):
        formset = kwargs.pop("formset", None)
        messages.warning(self.request, self.failure_message)
        return self.render_to_response(self.get_context_data(form=form, formset=formset))

    def form_valid(self, form, **kwargs):
        formset = kwargs.pop("formset", None)
        details = self._clean_formset(formset)
        try:
            with transaction.atomic():
                order = PurchaseAppService().create_purchase_order(
                    self._prepare_order(form.cleaned_data, details)
                )
                PurchaseOrchestrator().register_purchase(order, details)

                msg_success = self.success_message.format(model=self.model._meta.verbose_name)
                messages.success(self.request, msg_success, extra_tags="toast")
            return redirect(order.get_absolute_url())
        except ValidationError as e:
            self.handle_pydantic_error(e, form, formset)
            logger.error(f"Error creating purchase order: {e}", exc_info=True)
            return self.form_invalid(form, formset=formset)
        except Exception as e:
            logger.error(f"Error creating purchase order: {e}", exc_info=True)
            return self.handle_error(str(e), e)


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class PurchaseOrderUpdateView(PurchaseFormSetMixin, CustomUpdateView):
    model = DEFAULT_MODEL
    form_class = PurchaseOrderBase
    second_form_class = PurchaseOrderDetailFormSet
    success_url: str = DEFAULT_LIST_URL
    permission_required = ["operations.change_purchaseorder"]
    template_name = "operations/inbound/create_or_update.html"

    def get_formset(self, data=None):
        queryset = (
            self.object.details.select_related("batch").all()
            if self.object
            else PurchaseOrderDetail.objects.none()
        )

        formset = self.second_form_class(
            data=data, prefix="movements", queryset=queryset, instance=self.object
        )

        if not data:
            for form in formset.forms:
                print(form.instance.batch.expiry_date)
                if form.instance.pk and form.instance.batch:
                    form.initial["batch_number"] = form.instance.batch.batch_number
                    form.initial["expiry_date"] = form.instance.batch.expiry_date.strftime(
                        "%Y-%m-%d"
                    )
                    form.initial["supply"] = form.instance.supply.code

        return formset

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        post_data = request.POST.copy()
        for key in list(post_data.keys()):
            if "__prefix__" in key:
                del post_data[key]
        formset = self.get_formset(data=post_data)

        if form.is_valid() and formset.is_valid():
            return self.form_valid(form, formset=formset)

        return self.form_invalid(form, formset=formset)

    def form_invalid(self, form, **kwargs):
        formset = kwargs.pop("formset", None)
        messages.warning(self.request, self.failure_message)
        return self.render_to_response(self.get_context_data(form=form, formset=formset))

    def form_valid(self, form, **kwargs):
        formset = kwargs.pop("formset", None)
        details = self._clean_formset(formset)
        try:
            with transaction.atomic():
                order = PurchaseAppService().update_purchase_order(
                    instance=self.object, payload=self._prepare_order(form.cleaned_data, details)
                )
                PurchaseOrchestrator().update_purchase_order(order, details)

                msg_success = self.success_message.format(
                    model=self.model._meta.verbose_name, instance=order.order_number
                )
                messages.success(self.request, msg_success, extra_tags="toast")
                return redirect(order.get_absolute_url())
        except ValidationError as e:
            self.handle_pydantic_error(e, form, formset)
            logger.error(f"Error updating purchase order: {e}", exc_info=True)
            return self.form_invalid(form, formset=formset)
        except Exception as e:
            logger.error(f"Error updating purchase order: {e}", exc_info=True)
            return self.handle_error(str(e), e)


class MarkOrderCompletedView(View):
    def post(self, request, external_id):
        orchestrator = PurchaseOrchestrator()
        order = get_object_or_404(PurchaseOrder, external_id=external_id)

        try:
            orchestrator.complete_purchase_order(order)
            messages.success(request, _("Order completed successfully."))
        except Exception as e:
            logger.error(_(f"Error completing order: {e}"))
            messages.error(request, _("Failed to complete order."))

        return redirect(order.get_absolute_url())


class MarkOrderCancelView(View):
    def post(self, request, external_id):
        orchestrator = PurchaseOrchestrator()
        order = get_object_or_404(PurchaseOrder, external_id=external_id)

        try:
            orchestrator.cancel_purchase_order(order)
            messages.success(request, _("Order cancel successfully."))
        except Exception as e:
            logger.error(_(f"Error cancel order: {e}"))
            messages.error(request, _("Failed to cancel order."))

        return redirect(order.get_absolute_url())
