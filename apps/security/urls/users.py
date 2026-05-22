from django.urls import path

from apps.security.views.users import (
    UserCreateView,
    UserListView,
    UserPasswordUpdateView,
    UserUpdateView,
UserStatusUpdateView
)

app_name = "users"

SLUG = "<uuid:external_id>"

urlpatterns = [
    path("", UserListView.as_view(), name="list"),
    path("create/", UserCreateView.as_view(), name="create"),
    path(f"{SLUG}/update/", UserUpdateView.as_view(), name="update"),
    path(f"{SLUG}/update-status/", UserStatusUpdateView.as_view(), name="status"),
    path(f"{SLUG}/update-password/", UserPasswordUpdateView.as_view(), name="password_change"),
]
