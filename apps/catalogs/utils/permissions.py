from django.utils.translation import gettext_lazy as _


class Permissions:
    groups_permissions = [
        # ──────────────────────────────────────────────
        # Specialist
        # ──────────────────────────────────────────────
        {
            "name": _("specialist"),
            "permissions": {
                "security": {
                    "details": [
                        "change_user",
                        "view_user",
                        "change_person",
                        "view_person",
                    ]
                },
                "catalogs": {
                    "details": [
                        "add_catalog",
                        "change_catalog",
                        "view_catalog",
                        "add_catalogitem",
                        "change_catalogitem",
                        "view_catalogitem",
                    ]
                },
                "operations": {
                    "details": [
                        "add_supplier",
                        "change_supplier",
                        "view_supplier",
                    ]
                },
                "inventory": {
                    "details": [
                        "add_supply",
                        "change_supply",
                        "view_supply",
                        "add_batch",
                        "change_batch",
                        "view_batch",
                    ]
                },
            },
        },
        # ──────────────────────────────────────────────
        # Administrator
        # ──────────────────────────────────────────────
        {
            "name": _("administrator"),
            "permissions": {
                "admin": {
                    "details": [
                        "add_logentry",
                        "change_logentry",
                        "delete_logentry",
                        "view_logentry",
                    ]
                },
                "auth": {
                    "details": [
                        "add_permission",
                        "change_permission",
                        "delete_permission",
                        "view_permission",
                        "add_group",
                        "change_group",
                        "delete_group",
                        "view_group",
                    ]
                },
                "contenttypes": {
                    "details": [
                        "add_contenttype",
                        "change_contenttype",
                        "delete_contenttype",
                        "view_contenttype",
                    ]
                },
                "sessions": {
                    "details": [
                        "add_session",
                        "change_session",
                        "delete_session",
                        "view_session",
                    ]
                },
                "auditlog": {
                    "details": [
                        "add_logentry",
                        "change_logentry",
                        "delete_logentry",
                        "view_logentry",
                    ]
                },
                "django_celery_beat": {
                    "details": [
                        "add_crontabschedule",
                        "change_crontabschedule",
                        "delete_crontabschedule",
                        "view_crontabschedule",
                        "add_intervalschedule",
                        "change_intervalschedule",
                        "delete_intervalschedule",
                        "view_intervalschedule",
                        "add_periodictask",
                        "change_periodictask",
                        "delete_periodictask",
                        "view_periodictask",
                        "add_periodictasks",
                        "change_periodictasks",
                        "delete_periodictasks",
                        "view_periodictasks",
                        "add_solarschedule",
                        "change_solarschedule",
                        "delete_solarschedule",
                        "view_solarschedule",
                        "add_clockedschedule",
                        "change_clockedschedule",
                        "delete_clockedschedule",
                        "view_clockedschedule",
                    ]
                },
                "security": {
                    "details": [
                        "add_user",
                        "change_user",
                        "delete_user",
                        "view_user",
                        "add_person",
                        "change_person",
                        "delete_person",
                        "view_person",
                    ]
                },
                "catalogs": {
                    "details": [
                        "add_catalog",
                        "change_catalog",
                        "view_catalog",
                        "add_catalogitem",
                        "change_catalogitem",
                        "view_catalogitem",
                    ]
                },
                "operations": {
                    "details": [
                        "add_supplier",
                        "change_supplier",
                        "view_supplier",
                    ]
                },
                "inventory": {
                    "details": [
                        "add_supply",
                        "change_supply",
                        "view_supply",
                        "add_batch",
                        "change_batch",
                        "view_batch",
                    ]
                },
            },
        },
    ]
