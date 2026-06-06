from django import template
from django.urls import NoReverseMatch, reverse

register = template.Library()


@register.simple_tag(takes_context=True)
def active(context, url_name, css_class="active"):
    request = context.get("request")
    if not request:
        return ""

    path = request.path
    try:
        resolved_url = reverse(url_name)
    except NoReverseMatch:
        resolved_url = url_name

    if resolved_url == "/":
        return css_class if path == "/" else ""

    if path.startswith(resolved_url):
        return css_class

    return ""


@register.filter(name="has_group")
def has_group(user, group_names):
    groups = [g.strip() for g in group_names.split(",")]
    return user.groups.filter(name__in=groups).exists()
