import json

from django import template
from django.utils.safestring import mark_safe
from django.utils.text import capfirst

register = template.Library()


@register.simple_tag
def get_base_href() -> str:
    """Returns the base prefix configured in settings."""
    return ""


@register.filter
def object_verbose_name(obj) -> str:
    """Returns the human-readable name of the model (singular)."""
    return obj._meta.verbose_name


@register.filter
def object_verbose_name_plural(obj) -> str:
    """Returns the human-readable name of the model (plural)."""
    return obj._meta.verbose_name_plural


@register.filter
def field_label(obj, field_name):
    return obj._meta.get_field(field_name).verbose_name


@register.simple_tag
def label(obj, field_name):
    """Uso: {% label notification 'type' %}."""
    field = obj._meta.get_field(field_name)
    return capfirst(field.verbose_name)


@register.filter
def has_group(user, groups: str) -> bool:
    """Checks whether the user belongs to any of the given groups.

    Args:
        user (User): User instance.
        groups (str): Comma-separated list of group names.

    Returns:
        bool: True if the user belongs to any group, False otherwise.
    """
    return user.groups.filter(name__in=groups.split(",")).exists()


@register.filter
def pretty_json(value):
    """Formatea JSON para visualización en templates."""
    if not value:
        return ""

    try:
        # Si ya es string, cargarlo como JSON
        if isinstance(value, str):
            parsed = json.loads(value)
        else:
            parsed = value

        # Formatear con indentación
        formatted = json.dumps(parsed, indent=4, ensure_ascii=False)
        return mark_safe(f"<pre>{formatted}</pre>")
    except (TypeError, ValueError, json.JSONDecodeError):
        # Si falla, devolver el valor original como string
        return str(value)
