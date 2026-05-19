from django.urls import path

from apps.security.views.users import UserCreateView

urlpatterns = [
    path("", UserCreateView.as_view(), name="create_user"),
]
