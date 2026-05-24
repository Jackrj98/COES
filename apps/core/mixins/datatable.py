import logging

from django.http import JsonResponse

from apps.core.layers.dto import DataTableParams

logger = logging.getLogger(__name__)


class DatatableMixin:
    """A mixin for generically integrating DataTables into class-based views."""

    def get(self, request, *args, **kwargs):
        is_ajax = request.META.get(
            "HTTP_X_REQUESTED_WITH"
        ) == "XMLHttpRequest" or "application/json" in request.META.get("HTTP_ACCEPT", "")
        if is_ajax:
            return self.handle_datatable_request(request)
        return super().get(request, *args, **kwargs)

    def handle_datatable_request(self, request):
        params = DataTableParams(request, **request.GET)
        try:
            result = self.retrieve_data(params)
            return JsonResponse(result, safe=False)
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Error en Datatable: {e}", exc_info=True)
            return JsonResponse(params.result([]))

    def retrieve_data(self, params):
        raise NotImplementedError(
            f"You must implement `retrieve_data` in {self.__class__.__name__}"
        )
