from django.urls import path

from apps.security.views.auth import SignInView, SignOutView

urlpatterns = [
    path("login/", SignInView.as_view(), name="login"),
    path("logout/", SignOutView.as_view(), name="logout"),
]
