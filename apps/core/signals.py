from django.contrib.auth.models import Group, Permission
from django.db.models import Q
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from apps.core.utils.permissions import Permissions


@receiver(post_migrate)
def populate_groups_permissions(sender, **kwargs):
    """Populate groups and permissions automatically after migrations."""
    if sender.label != "core":
        return

    print("\n" + "=" * 60)
    print("SYNCHRONIZING GROUPS AND PERMISSIONS...")
    print("=" * 60)

    for group_data in Permissions.groups_permissions:
        group_name = str(group_data.get("name"))

        if not group_name:
            continue

        group, created = Group.objects.get_or_create(name=group_name)

        permissions = group_data.get("permissions", {})
        permission_query = Q()

        for app_name, app_permissions in permissions.items():
            detail_permissions = app_permissions.get("details", [])
            model_permissions = app_permissions.get("models", [])

            app_query = Q(content_type__app_label=app_name)

            detail_query = Q()
            model_query = Q()

            if detail_permissions:
                detail_query = Q(codename__in=detail_permissions)

            if model_permissions:
                model_query = Q(content_type__model__in=model_permissions)

            permission_query |= app_query & (detail_query | model_query)

        matched_permissions = list(Permission.objects.filter(permission_query).distinct())

        group.permissions.set(matched_permissions)

        status = "Created" if created else " Updated"
        codenames = [p.codename for p in matched_permissions]

        print(f"\n[{status}] Group: '{group_name}'")
        print(f"  └─ Permissions count: {len(codenames)}")

    print("\n" + "=" * 60)
    print("GROUPS AND PERMISSIONS SYNCHRONIZATION FINISHED")
    print("=" * 60 + "\n")
