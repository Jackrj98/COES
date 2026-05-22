from enum import Enum

from django.utils.translation import gettext_lazy as _


class LabelEnum(Enum):
    ADD_MODEL = _("Add {model}")
    EDIT_MODEL = _("Edit {model}")
    STATUS_MODEL = _("{state} {model}")
    DELETE_MODEL = _("Delete {model}")
    LIST_MODEL = _("List of {model}")
    DETAILS_MODEL = _("Details of {model}")
    IMPORT_MODEL = _("Import {model}")
    ACTIONS = _("Actionable")

    ADD = _("Add")
    EDIT = _("Edit")
    STATUS = _("Change status")
    DELETE = _("Delete")
    DETAILS = _("Details")
    IMPORT = _("Import")
    EXPORT = _("Export")

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
    FAILURE_REQUEST = _("An unexpected error occurred while processing your request.")
    NOT_FOUND = _("The requested {model} '{identifier}' was not found.")
    ALREADY_EXISTS = _("A {model} with the specified attributes already exists.")

    def format(self, **kwargs):
        return str(self.value).format(**kwargs)
