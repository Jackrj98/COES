from enum import Enum

from django.utils.translation import gettext_lazy as _


class LabelEnum(Enum):
    ADD = _("Add {model}")
    EDIT = _("Edit {model}")
    STATUS = _("{state} {model}")
    DELETE = _("Delete {model}")
    LIST = _("List of {model}")
    DETAILS = _("Details of {model}")
    IMPORT = _("Import {model}")
    ACTIONS = _("Actionable")

    def format(self, **kwargs):
        return str(self.value).format(**kwargs)


class MessageEnum(Enum):
    # SUCCESS
    SUCCESS = _("The operation completed successfully.")
    CREATED = _("The {model} was successfully created.")
    UPDATED = _("The {model} '{instance}' was successfully updated.")
    DELETED = _("The {model} '{instance}' was successfully deleted.")

    # ERRORS
    FAILURE = _("An error has occurred, please try again.")
    NOT_FOUND = _("The requested {model} '{identifier}' was not found.")
    ALREADY_EXISTS = _("A {model} with the specified attributes already exists.")

    def format(self, **kwargs):
        return str(self.value).format(**kwargs)
