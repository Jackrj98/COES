from enum import Enum

from django.utils.translation import gettext_lazy as _


class MessagesEnum(Enum):
    # Users login
    INVALID_CREDENTIALS = _("The credentials are invalid, please try again.")
    INVALID_CREDENTIALS_WITH_ATTEMPTS = _(
        "The credentials are invalid, please try again. Attempts {number}"
    )
    USER_INACTIVE = _("The user has been deactivated, please contact the administrator.")
    USER_BLOCKED = _("The user has been blocked, please contact the administrator.")
    EMAIL_UNVERIFIED = _(
        "The email address is not verified. Please check your email inbox to verify the account."
    )

    # Password
    PASSWORD_CHANGED = _("The password has been changed")
    PASSWORD_INCORRECT = _("Current password is incorrect")
    FORCED_PASSWORD = _("The password needs to be updated. To continue browsing.")
    PASSWORD_RESET = _(
        "A link was sent to reset your password. Please check your email to continue."
    )

    def format(self, **kwargs):
        return str(self.value).format(**kwargs)
