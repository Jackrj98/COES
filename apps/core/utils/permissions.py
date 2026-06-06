from django.utils.translation import gettext_lazy as _


class Permissions:
    groups_permissions = [
        # Administrador
        {
            "name": _("administrator"),
            "permissions": {
                "security": {
                    "details": [
                        "add_user",
                        "change_user",
                        "view_user",
                        "add_person",
                        "change_person",
                        "view_person",
                        "add_usertoken",
                        "change_usertoken",
                        "view_usertoken",
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
                "inventory": {
                    "details": [
                        "add_batch",
                        "change_batch",
                        "view_batch",
                        "add_supply",
                        "change_supply",
                        "view_supply",
                        "add_inventorymovement",
                        "change_inventorymovement",
                        "view_inventorymovement",
                    ]
                },
                "operations": {
                    "details": [
                        "add_exitorder",
                        "change_exitorder",
                        "view_exitorder",
                        "add_supplier",
                        "change_supplier",
                        "view_supplier",
                        "add_purchaseorder",
                        "change_purchaseorder",
                        "view_purchaseorder",
                        "add_exitdetail",
                        "change_exitdetail",
                        "view_exitdetail",
                        "add_purchaseorderdetail",
                        "change_purchaseorderdetail",
                        "view_purchaseorderdetail",
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
            },
        },
        # Specialist
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
                "inventory": {
                    "details": [
                        "add_batch",
                        "change_batch",
                        "view_batch",
                        "add_supply",
                        "change_supply",
                        "view_supply",
                        "add_inventorymovement",
                        "change_inventorymovement",
                        "view_inventorymovement",
                    ]
                },
                "operations": {
                    "details": [
                        "add_exitorder",
                        "view_exitorder",
                        "add_supplier",
                        "change_supplier",
                        "view_supplier",
                        "add_purchaseorder",
                        "change_purchaseorder",
                        "view_purchaseorder",
                        "add_exitdetail",
                        "view_exitdetail",
                        "add_purchaseorderdetail",
                        "change_purchaseorderdetail",
                        "view_purchaseorderdetail",
                    ]
                },
            },
        },
    ]
