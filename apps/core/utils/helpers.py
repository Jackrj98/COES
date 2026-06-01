import os
import uuid


def generate_upload_path(instance, filename: str) -> str:
    """Generate dynamic upload path.

    Example:
        clinics/clinic/clinic_<uuid>.png
    """
    meta = instance._meta  # noqa
    app_label = meta.app_label
    model_name = meta.model_name

    extension = os.path.splitext(filename)[1]
    filename = f"{model_name}_{uuid.uuid4().hex}{extension}"

    return os.path.join(app_label, model_name, filename)
