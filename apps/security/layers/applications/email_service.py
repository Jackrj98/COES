import logging
from django.utils import translation

from apps.security.tasks import send_email_async

logger = logging.getLogger(__name__)


class EmailAppService:
    @staticmethod
    def send(subj: str, recp: list, template: str, ctx: dict) -> bool:
        send_email_async.delay(
            subj,
            recp,
            template,
            ctx,
            language=translation.get_language(),
        )
        return True
