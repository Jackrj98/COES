from django.urls import path

from apps.security.views.users import (
    UserCreateView,
    UserDetailView,
    UserListView,
    UserPasswordUpdateView,
    UserStatusUpdateView,
    UserUpdateView,
    send_reset_password,
)

app_name = "users"
SLUG = "<uuid:external_id>"

urlpatterns = [
    path("", UserListView.as_view(), name="list"),
    path(f"{SLUG}/", UserDetailView.as_view(), name="detail"),
    path("create/", UserCreateView.as_view(), name="create"),
    path(f"{SLUG}/update/", UserUpdateView.as_view(), name="update"),
    path(f"{SLUG}/update-status/", UserStatusUpdateView.as_view(), name="status"),
    path(f"{SLUG}/password/", UserPasswordUpdateView.as_view(), name="password_change"),
    path(f"{SLUG}/password-reset/", send_reset_password, name="password_reset"),
]
