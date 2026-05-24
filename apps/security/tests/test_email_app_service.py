from unittest.mock import patch

import pytest

from apps.security.layers.applications import EmailAppService


class TestEmailAppService:
    @pytest.fixture
    def service(self):
        return EmailAppService()

    @patch("apps.security.layers.applications.email_service.send_email_async.delay")
    @patch("apps.security.layers.applications.email_service.translation.get_language")
    def test_send_success(self, mock_get_language, mock_delay, service):
        mock_get_language.return_value = "es"

        subj = "Test Subject"
        recp = ["test@example.com"]
        template = "template.html"
        ctx = {"name": "User"}

        result = service.send(subj, recp, template, ctx)

        assert result is True
        mock_delay.assert_called_once_with(subj, recp, template, ctx, language="es")

    @patch("apps.security.layers.applications.email_service.send_email_async")
    def test_send_failure(self, mock_send_email_async, service):
        mock_send_email_async.delay.side_effect = Exception("Celery error")

        with pytest.raises(Exception, match="Celery error"):
            service.send("Subj", ["recp"], "tmp", {})
