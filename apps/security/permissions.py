from django.contrib.auth.models import Group, Permission
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

GROUP_NAMES = {
    "administrator": "administrator",
    "specialist": "specialist",
}

ALL_GROUP_NAMES = list(GROUP_NAMES.values())

ROLES = {
    "administrator": {
        "name": _("administrator"),
        "permissions": {
            "security": {
                "details": [
                    "add_person",
                    "change_person",
                    "view_person",
                    "add_user",
                    "change_user",
                    "view_user",
                    "view_users",
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
                    "view_catalogs",
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
                    "view_supplies",
                    "view_inventorymovements",
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
                    "view_exitorders",
                    "view_suppliers",
                    "view_purchaseorders",
                ]
            },
            "sessions": {"details": ["add_session", "change_session", "view_session"]},
        },
    },
    "specialist": {
        "name": _("specialist"),
        "permissions": {
            "security": {
                "details": [
                    "change_person",
                    "view_person",
                    "change_user",
                    "view_user",
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
                    "view_catalogs",
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
                    "view_supplies",
                    "view_inventorymovements",
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
                    "view_exitorders",
                    "view_suppliers",
                    "view_purchaseorders",
                ]
            },
            "sessions": {"details": ["add_session", "change_session", "view_session"]},
        },
    },
}


def get_role_names() -> list[str]:
    return list(ROLES.keys())


def get_permissions_for_role(role_name: str) -> list[str]:
    """Return all permissions for a given role."""
    role = ROLES.get(role_name)
    if not role:
        return []

    codenames = []
    for app_section in role.get("permissions", {}).values():
        codenames.extend(app_section.get("details", []))
        codenames.extend(app_section.get("models", []))
    return codenames


def sync_roles_and_permissions(verbosity: int = 1) -> dict:
    """Sync roles and permissions from the ROLES constant."""
    results = {
        "created": 0,
        "updated": 0,
        "groups": [],
        "total_permissions_assigned": 0,
    }

    for role_key, role_data in ROLES.items():
        group_name = str(role_data.get("name"))
        if not group_name:
            continue

        group, created = Group.objects.get_or_create(name=group_name)

        if created:
            results["created"] += 1
        else:
            results["updated"] += 1

        permissions_dict = role_data.get("permissions", {})
        permission_query = Q()

        for app_label, section in permissions_dict.items():
            detail_codenames = section.get("details", [])
            model_names = section.get("models", [])

            app_q = Q(content_type__app_label=app_label)

            if detail_codenames:
                permission_query |= app_q & Q(codename__in=detail_codenames)
            if model_names:
                permission_query |= app_q & Q(content_type__model__in=model_names)

        matched = list(Permission.objects.filter(permission_query).distinct())
        group.permissions.set(matched)

        results["total_permissions_assigned"] += len(matched)
        results["groups"].append(
            {
                "name": group_name,
                "created": created,
                "permissions_count": len(matched),
            }
        )

        if verbosity >= 1:
            status = "Created" if created else "Updated"
            print(f"[{status}] Group: '{group_name}' — {len(matched)} permissions")

    if verbosity >= 1:
        print(
            f"\nPermissions sync finished. "
            f"Created: {results['created']}, Updated: {results['updated']}"
        )

    return results
