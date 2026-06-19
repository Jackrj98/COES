import logging

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from pydantic import ValidationError

from apps.core.views.base import (
    CustomCreateView,
    CustomDetailView,
    CustomListView,
    CustomUpdateView,
)
from apps.inventory.forms import BatchCreateForm, BatchFilterForm, BatchUpdateForm
from apps.inventory.layers.applications import BatchAppService, InventoryMovementAppService
from apps.inventory.models import Batch, InventoryMovement, Supply
from apps.security.layers.security import SecurityService

logger = logging.getLogger(__name__)

DEFAULT_MODEL = Batch
DEFAULT_LIST_URL = reverse_lazy("inventory:batches:list")


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class BatchListView(CustomListView):
    model = DEFAULT_MODEL
    form_class = BatchFilterForm
    slug_field = "supply__external_id"
    slug_url_kwarg = "supply_reference"
    success_url: str = DEFAULT_LIST_URL
    template_name = "supplies/datatable.html"
    permission_required = "inventory.view_batch"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        return ctx

    def retrieve_data(self, params):
        supply_reference = self.kwargs.get(self.slug_url_kwarg)
        return BatchAppService().retrieve_batches(params, supply_reference)

    def get_success_url(self):
        return self.success_url


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class BatchDetailView(CustomDetailView):
    """View for displaying supply details with stock information."""

    app_name = "supplies"
    model = DEFAULT_MODEL
    permission_required = "inventory.view_batch"
    template_name = "supplies/batches/detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        instance = self.object

        supply_kwargs = {"external_id": instance.supply.external_id}
        breadcrumbs = ctx.get("breadcrumb", [])
        breadcrumbs[0] = {
            "name": instance.supply.name,
            "url": reverse_lazy("inventory:supplies:detail", kwargs=supply_kwargs),
        }
        breadcrumbs.insert(
            0, {"name": _("Supplies"), "url": reverse_lazy("inventory:supplies:list")}
        )
        breadcrumbs[-1]["active"] = True
        ctx["breadcrumbs"] = breadcrumbs
        ctx["list_url"] = instance.get_absolute_url()
        ctx["cancel_url"] = instance.get_absolute_url()
        actions = ctx["actions"]
        actions["actions"][0]["url"] = reverse_lazy(
            "inventory:batches:update",
            kwargs={
                "external_id": instance.external_id,
                "supply_reference": instance.supply.external_id,
            },
        )
        ctx["actions"] = actions
        return ctx

    def get_success_url(self):
        supply_reference = self.kwargs.get("supply_reference")
        kwargs = {
            "supply_reference": supply_reference,
            "external_id": self.kwargs.get(self.slug_url_kwarg),
        }
        return reverse("inventory:batches:detail", kwargs=kwargs)


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class BatchCreateView(CustomCreateView):
    model = DEFAULT_MODEL
    second_model = Supply
    form_class = BatchCreateForm
    slug_url_kwarg = "supply_reference"
    permission_required = "inventory.add_batch"
    template_name = "supplies/batches/create.html"

    def get_supply(self):
        if not hasattr(self, "supply"):
            supply_reference = self.kwargs.get(self.slug_url_kwarg)
            self.supply = Supply.objects.get(external_id=supply_reference)  # noqa
        return self.supply

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        breadcrumbs = ctx.get("breadcrumb", [])
        breadcrumbs.insert(
            0, {"name": _("Supplies"), "url": reverse_lazy("inventory:supplies:list")}
        )

        supply = self.get_supply()
        breadcrumbs[1]["name"] = f"{supply.name} - {supply.code}"
        ctx["breadcrumbs"] = breadcrumbs
        return ctx

    def get_initial(self):
        initial = super().get_initial()
        initial["supply"] = self.get_supply()
        return initial

    def form_valid(self, form, **kwargs):
        service = BatchAppService()
        batch_data = form.cleaned_data

        try:
            # Prepare data for service layer
            batch_data["supply_id"] = self.get_supply().id
            new_batch = service.register_batch(payload=batch_data)
            self._register_initial_movement(new_batch, batch_data["initial_quantity"])

            new_batch.current_quantity = batch_data["initial_quantity"]
            new_batch.save(update_fields=["current_quantity"])
            # Show success message
            success_message = self.success_message.format(model=self.model._meta.verbose_name)
            messages.success(self.request, success_message, extra_tags="toast")

            # Redirect to the detail page
            return redirect(self.get_success_url())

        except ValidationError as e:
            self.handle_pydantic_error(e, form)
            return self.form_invalid(form)
        except Exception as e:
            return self.handle_error(str(e), e)

    def get_success_url(self):
        kwargs = {"external_id": self.kwargs.get("supply_reference")}
        return reverse("inventory:supplies:detail", kwargs=kwargs)

    @staticmethod
    def _register_initial_movement(batch: Batch, quantity: int) -> None:
        try:
            movement_payload = {
                "batch_id": batch.id,
                "movement_type": InventoryMovement.Type.INBOUND,
                "concept": str(_("Initial stock entry")),
                "quantity": quantity,
                "observation": str(
                    _("Batch creation with initial quantity: {quantity}").format(quantity=quantity)
                ),
                "previous_stock": 0,
                "after_stock": quantity,
                "unit_cost_at_movement": batch.unit_cost,
                "status": InventoryMovement.MovementStatusChoices.COMPLETED,
            }

            InventoryMovementAppService().register_movement(movement_payload)
            logger.info(f"Initial movement registered for batch {batch.id}: +{quantity}")

        except Exception as e:
            logger.warning(f"Failed to register initial movement for batch {batch.id}: {str(e)}")


@method_decorator(user_passes_test(SecurityService.require_access), name="dispatch")
class BatchUpdateView(CustomUpdateView):
    model = DEFAULT_MODEL
    form_class = BatchUpdateForm
    permission_required = "inventory.change_batch"
    template_name = "supplies/batches/update.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        instance = self.object
        supply_kwargs = {"external_id": instance.supply.external_id}

        breadcrumbs = ctx.get("breadcrumb", [])
        breadcrumbs[0] = {
            "name": instance.supply.name,
            "url": reverse_lazy("inventory:supplies:detail", kwargs=supply_kwargs),
        }
        breadcrumbs.insert(
            0, {"name": _("Supplies"), "url": reverse_lazy("inventory:supplies:list")}
        )
        ctx["breadcrumbs"] = breadcrumbs
        ctx["list_url"] = instance.get_absolute_url()
        ctx["cancel_url"] = instance.get_absolute_url()
        return ctx

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def form_valid(self, form):
        """Handle valid form submission with proper old/new quantity comparison."""
        try:
            batch_instance = self.object
            old_quantity = self._get_original_quantity(batch_instance)
            new_quantity = form.cleaned_data.get("current_quantity", old_quantity)

            payload = self._build_batch_dto(form, batch_instance, new_quantity)
            if self._has_quantity_changed(old_quantity, new_quantity):
                self._register_stock_movement(
                    batch_instance, old_quantity, new_quantity, payload["adjustment_reason"]
                )

            updated_batch = self._update_batch(batch_instance, payload)
            success_message = self.success_message.format(
                model=self.model._meta.verbose_name, instance=updated_batch.batch_number[:10]
            )
            messages.success(self.request, success_message, extra_tags="toast")

            return redirect(updated_batch.get_absolute_url())

        except ValidationError as e:
            self.handle_pydantic_error(e, form)
            return self.form_invalid(form)
        except Exception as e:
            return self.handle_error(str(e), e)

    def get_success_url(self):
        kwargs = {"external_id": self.kwargs.get("supply_reference")}
        return reverse("inventory:supplies:detail", kwargs=kwargs)

    def _get_supply_from_kwargs(self):
        """Retrieve supply from URL parameters."""
        supply_id = self.kwargs.get("supply_reference")
        return Supply.objects.get(external_id=supply_id)

    @staticmethod
    def _get_original_quantity(batch_instance: Batch) -> int:
        """Retrieve the original quantity from the database before any changes."""
        try:
            original_batch = Batch.objects.get(pk=batch_instance.pk)
            return original_batch.current_quantity
        except Batch.DoesNotExist:
            return 0

    @staticmethod
    def _has_quantity_changed(old_quantity: int, new_quantity: int) -> bool:
        """Check if quantity has actually changed."""
        return new_quantity != old_quantity

    @staticmethod
    def _build_batch_dto(form, batch_instance: Batch, new_quantity: int):
        """Build Batch DTO from form data."""
        batch_data = form.cleaned_data

        batch_data["supply_id"] = batch_instance.supply_id
        batch_data["initial_quantity"] = batch_instance.initial_quantity

        return batch_data

    def _register_stock_movement(
        self, batch: Batch, old_quantity: int, new_quantity: int, concept: str
    ) -> None:
        """Register inventory movement for quantity adjustment."""
        diff = new_quantity - old_quantity

        movement_payload = self._build_movement_payload(
            batch=batch,
            old_quantity=old_quantity,
            new_quantity=new_quantity,
            diff=diff,
            concept=concept,
        )

        logger.info(f"Registering stock adjustment: {diff:+d} units for batch {batch.id}")
        InventoryMovementAppService().register_movement(movement_payload)

    @staticmethod
    def _build_movement_payload(batch, old_quantity, new_quantity, diff, concept) -> dict:
        """Build a payload for inventory movement registration."""
        return {
            "batch_id": batch.id,
            "movement_type": InventoryMovement.Type.ADJUSTMENT,
            "concept": concept,
            "quantity": abs(diff),
            "observation": f"Ajuste manual: {old_quantity} → {new_quantity} (Diferencia: {diff:+d})",
            "previous_stock": old_quantity,
            "after_stock": new_quantity,
            "unit_cost_at_movement": batch.unit_cost,
            "status": InventoryMovement.MovementStatusChoices.COMPLETED,
        }

    @staticmethod
    def _update_batch(batch_instance: Batch, payload) -> Batch:
        """Update a batch using the service layer."""
        service = BatchAppService()
        return service.update_batch(instance=batch_instance, payload=payload)
