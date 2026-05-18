from django.contrib import admin
from django.utils.translation import gettext_lazy as _


class BaseAdminMixin(admin.ModelAdmin):
    list_per_page = 25
    empty_value_display = "-"
    PRIMARY_IDENTIFIER = "external_id"
    AUDIT_LOG_FIELDS = ("created_at", "created_by", "updated_at", "updated_by", "deleted_at")
    ALL_AUDIT_FIELDS = (PRIMARY_IDENTIFIER,) + AUDIT_LOG_FIELDS

    actions = ["activate_records", "deactivate_records"]

    def get_readonly_fields(self, request, obj=None):
        readonly = super().get_readonly_fields(request, obj)
        return tuple(set(list(readonly) + list(self.ALL_AUDIT_FIELDS)))

    def get_list_display(self, request):
        child_fields = list(super().get_list_display(request))
        clean_child_fields = [f for f in child_fields if f not in self.ALL_AUDIT_FIELDS]

        return (self.PRIMARY_IDENTIFIER,) + tuple(clean_child_fields) + self.AUDIT_LOG_FIELDS

    def get_fieldsets(self, request, obj=None):
        fieldsets = list(super().get_fieldsets(request, obj))
        audit_title = _("Audit Information")

        if not any(fs[0] and str(fs[0]) == str(audit_title) for fs in fieldsets):
            audit_fieldset = (
                str(audit_title),
                {
                    "classes": ("collapse", "wide"),
                    "fields": [
                        self.PRIMARY_IDENTIFIER,
                        ["created_at", "created_by"],
                        ["updated_at", "updated_by"],
                        "deleted_at",
                    ],
                },
            )
            fieldsets.append(audit_fieldset)

        return fieldsets

    @admin.action(description=_("Mark selected items as active"))
    def activate_records(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, _("%d records marked as active.") % updated)

    @admin.action(description=_("Mark selected items as inactive"))
    def deactivate_records(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, _("%d records marked as inactive.") % updated)
