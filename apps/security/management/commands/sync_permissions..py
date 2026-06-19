from django.core.management.base import BaseCommand

from apps.security.permissions import sync_roles_and_permissions


class Command(BaseCommand):
    help = "Sync roles and permissions"

    def add_arguments(self, parser):
        parser.add_argument(
            "--verbosity",
            type=int,
            default=1,
            choices=[0, 1, 2],
            help="Level of verbosity.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
        )

    def handle(self, *args, **options):
        verbosity = options["verbosity"]
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made."))
            return

        self.stdout.write("Syncing roles and permissions...")

        results = sync_roles_and_permissions(verbosity=verbosity)

        self.stdout.write(
            self.style.SUCCESS(
                f"\n Sync complete. Created: {results['created']}, Updated: {results['updated']}"
            )
        )
