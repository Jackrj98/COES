import logging
from smtplib import SMTPAuthenticationError

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


class EmailBuilder:
    def __init__(self):
        self.subject = None
        self.recipients = []
        self.message = None
        self.template = None
        self.context = {}
        self.fail_silently = False
        self.from_email = settings.EMAIL_HOST_USER

    def set_subject(self, subject: str):
        self.subject = subject
        return self

    def set_recipients(self, recipients: list[str]):
        self.recipients = recipients
        return self

    def add_recipient(self, recipient: str):
        if recipient not in self.recipients:
            self.recipients.append(recipient)
        return self

    def set_message(self, message: str):
        self.message = message
        return self

    def set_template(self, template_path: str):
        self.template = template_path
        return self

    def set_context(self, context: dict):
        self.context = context
        return self

    def add_context(self, key: str, value):
        self.context[key] = value
        return self

    def _build_html_content(self) -> str:
        if self.template and self.context:
            return render_to_string(self.template, self.context)
        elif self.message:
            return self.message
        else:
            raise ValueError("A message or a template with its context should be provided")

    def build(self) -> dict:
        if not self.subject:
            raise ValueError("Email subject is required")
        if not self.recipients:
            raise ValueError("At least one recipient is required")

        html_content = self._build_html_content()

        return {
            "subject": self.subject,
            "message": strip_tags(html_content),
            "from_email": self.from_email,
            "recipient_list": self.recipients,
            "html_message": html_content,
        }

    def send(self) -> bool:
        try:
            email_data = self.build()
            result = send_mail(
                **email_data,
                fail_silently=self.fail_silently,
            )
            logger.info(f"Email sent successfully to {self.recipients}")
            return result > 0

        except SMTPAuthenticationError:
            logger.error("The mail could not be sent. Check the SMTP settings.")
            return False
        except Exception as e:
            logger.error(f"Error sending mail: {str(e)}")
            return False
