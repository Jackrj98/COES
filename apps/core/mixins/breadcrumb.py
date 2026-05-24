from django.utils.translation import gettext_lazy as _

from apps.core.utils.constants import LabelEnum


class BreadcrumbMixin:
    breadcrumb_display_field = None

    def get_breadcrumb_display_name(self, instance):
        if self.breadcrumb_display_field:
            return getattr(instance, self.breadcrumb_display_field, str(instance))
        return str(instance)

    def build_breadcrumb(self, extra_breadcrumb=None):
        if not self.model:  # noqa
            return []

        verbose_name_plural = _(self.model._meta.verbose_name_plural).title()  # noqa
        breadcrumb = [
            {
                "name": verbose_name_plural,
                "url": self.get_success_url(),  # noqa
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
            if extra_breadcrumb:
                breadcrumb.append(extra_breadcrumb)
        else:
            breadcrumb[-1]["active"] = True

        return breadcrumb
