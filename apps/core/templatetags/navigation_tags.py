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
