from django.utils.translation import gettext_lazy as _

from apps.core.utils.constants import LabelEnum


class BreadcrumbMixin:
    breadcrumb_display_field = None

    def get_breadcrumb_display_name(self, instance):
        if self.breadcrumb_display_field:
            return getattr(instance, self.breadcrumb_display_field, str(instance))
        return str(instance)

    def build_breadcrumb(self, extra_breadcrumb=None):
        if not self.model:
            return []

        verbose_name_plural = _(self.model._meta.verbose_name_plural).title()
        breadcrumb = [
            {
                "name": verbose_name_plural,
                "url": self.get_success_url(),
                "active": False,
                "title": LabelEnum.LIST.format(model=verbose_name_plural),
            }
        ]

        instance = getattr(self, "object", None)
        if instance:
            display_name = self.get_breadcrumb_display_name(instance)
            breadcrumb.append(
                {
                    "name": display_name,
                    "url": instance.get_absolute_url(),
                    "active": False,
                    "title": display_name,
                }
            )
            breadcrumb[-1]["active"] = False
        else:
            breadcrumb[-1]["active"] = True

        if extra_breadcrumb:
            if len(breadcrumb) > 1:
                breadcrumb[-2]["active"] = False
            else:
                breadcrumb[0]["active"] = False

            breadcrumb.append(extra_breadcrumb)

        return breadcrumb
