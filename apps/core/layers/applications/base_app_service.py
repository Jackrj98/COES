from django.core.exceptions import ValidationError
from django.db.models import Model


class BaseAppService:
    def __init__(self, model=None):
        self.model = model

    def retrieve_by_external(self, external_id) -> "model":  # noqa: F821
        """Fetches the first active object with the given external ID.

        Args:
            external_id: The unique identifier used to fetch the active object.

        Returns:
            Model: The first matching active object, or None if no match is found.
        """
        return self.model.active.filter(external_id=external_id).first()

    @staticmethod
    def normalize_data(data, remove_spaces=False, to_lowercase=True):
        if not isinstance(data, str):
            return data

        normalized = data.strip().strip("'")
        if to_lowercase:
            normalized = normalized.lower()
        if remove_spaces:
            normalized = normalized.replace(" ", "")
        return normalized

    @staticmethod
    def validate_required_fields(required_fields: list, payload: dict) -> bool:
        """Validates that the required fields are present in the data.

        Args:
            payload (dict): The input data.
            required_fields (list): A list of required field names.

        Raises:
            ValidationError: If any required field is missing.

        Returns:
            bool: Whether the required fields are present.
        """
        for field in required_fields:
            if not payload.get(field):
                raise ValidationError(f"{field.capitalize()} is required.")

        return True

    @staticmethod
    def update_fields(instance, **fields):
        """Update the fields of a model instance.

        Args:
            instance (Model): The model class.
            fields (dict): The fields to update.

        Returns:
            Model: The model instance.
        """
        if not isinstance(instance, Model):
            raise ValueError(f"Invalid {instance._meta.verbose_name} instance provided")

        for field, value in fields.items():
            if hasattr(instance, field):
                setattr(instance, field, value)

        instance.save()
        return instance

    @staticmethod
    def get_detail_url(name, **kwargs):
        from django.urls import reverse_lazy

        return reverse_lazy(name, kwargs=kwargs)
