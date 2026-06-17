from django.urls import include, path

app_name = "operations"
urlpatterns = [
    path("suppliers/", include("apps.operations.urls.suppliers")),
    path("exit/orders/", include("apps.operations.urls.outbound_order")),
    path("outbound/orders/", include("apps.operations.urls.outbound_orders")),
    path("inbound/orders/", include("apps.operations.urls.inbound_orders")),
]
