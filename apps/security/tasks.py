from celery import shared_task
from django.conf import settings
from django.utils import translation

from apps.security.layers.builders import EmailBuilder


@shared_task
def send_email_async(subj, recp, template, ctx, language=None):
    lang = language or settings.LANGUAGE_CODE
    translation.activate(lang)
    try:
        builder = (
            EmailBuilder()
            .set_subject(subj)
            .set_recipients(recp)
            .set_template(template)
            .set_context(ctx)
        )
        return builder.send()
    finally:
        translation.deactivate()