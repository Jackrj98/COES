import pytest
from django.conf import settings
from django.contrib.messages import get_messages
from django.urls import reverse

from apps.security.models import User
from apps.security.utils.constants import MessagesEnum


@pytest.mark.django_db
class TestSignInView:
    LOGIN_URL = reverse("security:login")
    LIST_URL = reverse("security:users:list")

    def _post_login(self, client, username, password):
        return client.post(self.LOGIN_URL, {"username": username, "password": password})

    def _assert_message(self, response, message_enum):
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        assert any(str(message_enum.value) in m for m in messages)

    # --- Tests ---

    @pytest.mark.parametrize(
        "user_fixture, expected_access",
        [("admin_user_unauthenticated", 200), ("specialist_user_unauthenticated", 200)],
    )
    def test_login_success_by_role(self, client, request, user_fixture, expected_access):
        user = request.getfixturevalue(user_fixture)
        response = self._post_login(client, user.username, "Password123!")

        assert response.status_code == 302
        assert response.url == settings.LOGIN_REDIRECT_URL
        assert client.get(settings.LOGIN_REDIRECT_URL).status_code == expected_access

    @pytest.mark.parametrize(
        "user_fixture", ["admin_user_unauthenticated", "specialist_user_unauthenticated"]
    )
    def test_login_fails_with_wrong_password(self, client, request, user_fixture):
        user = request.getfixturevalue(user_fixture)
        response = self._post_login(client, user.username, "WrongPassword!")

        assert response.status_code == 200

        messages = [str(m) for m in get_messages(response.wsgi_request)]
        expected = str(MessagesEnum.INVALID_CREDENTIALS_WITH_ATTEMPTS.value.format(number=4))
        assert any(expected in m for m in messages)

    @pytest.mark.parametrize("group", ["administrator", "specialist"])
    def test_force_password_user_redirected(self, client, user_factory, group):
        user = user_factory(force_password=True, groups=[group])
        response = self._post_login(client, user.username, "Password123!")

        expected_url = reverse(
            "security:users:password_change", kwargs={"external_id": user.external_id}
        )
        assert response.status_code == 302
        assert response.url == expected_url
        self._assert_message(response, MessagesEnum.FORCED_PASSWORD)

    @pytest.mark.parametrize("client_fixture", ["admin_client", "specialist_client"])
    def test_authenticated_user_redirected(self, request, client_fixture):
        client, _ = request.getfixturevalue(client_fixture)
        response = client.get(self.LOGIN_URL)
        assert response.status_code == 302
        assert response.url == settings.LOGIN_REDIRECT_URL

    @pytest.mark.parametrize(
        "user_fixture, msg_enum",
        [
            ("admin_user_unauthenticated", MessagesEnum.USER_INACTIVE),
            ("specialist_user_unauthenticated", MessagesEnum.USER_INACTIVE),
            ("admin_user_unauthenticated", MessagesEnum.USER_BLOCKED),
            ("specialist_user_unauthenticated", MessagesEnum.USER_BLOCKED),
        ],
    )
    def test_disabled_user_cannot_login(self, client, request, user_fixture, msg_enum):
        user = request.getfixturevalue(user_fixture)
        if msg_enum == MessagesEnum.USER_INACTIVE:
            user.is_active = False
        else:
            user.status = User.Status.LOCKED
        user.save()

        response = self._post_login(client, user.username, "Password123!")

        assert response.status_code == 200
        self._assert_message(response, msg_enum)
        assert client.get(self.LIST_URL).status_code == 302

    def test_login_max_failed_attempts_locks_account(self, client, user_factory):
        user = user_factory(groups=["specialist"])
        for _ in range(5):
            self._post_login(client, user.username, "WrongPassword!")

        user.refresh_from_db()
        assert user.status == User.Status.LOCKED

        response = self._post_login(client, user.username, "Password123!")
        self._assert_message(response, MessagesEnum.USER_BLOCKED)
