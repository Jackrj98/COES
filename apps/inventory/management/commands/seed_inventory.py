import random

from django.core.management.base import BaseCommand
from faker import Faker

from apps.catalogs.models import Catalog, CatalogItem
from apps.inventory.models import Batch, Supply


class Command(BaseCommand):
    help = "Generates mock data for Supplies and Batches"

    def add_arguments(self, parser):
        parser.add_argument("--number", type=int, default=10, help="Number of supplies to create")

    def handle(self, *args, **options):
        fake = Faker()
        fake.unique.clear()
        count = options["number"]

        categories = CatalogItem.objects.filter(catalog__code=Catalog.CatalogCodes.SUPPLY_CATEGORY)
        units = CatalogItem.objects.filter(catalog__code=Catalog.CatalogCodes.UNIT_OF_MEASURE)

        if not categories.exists() or not units.exists():
            self.stdout.write(
                self.style.ERROR("Error: Ensure CatalogItems exist for categories and units first.")
            )
            return

        supplies_created = []

        for _ in range(count):
            category = random.choice(categories)
            supply = Supply.objects.create(
                name=fake.unique.word().title(),
                code=fake.unique.bothify(text=f"{category.extra}-####"),
                description=fake.sentence(),
                stock_min=random.randint(5, 50),
                category=category,
                unit_of_measure=random.choice(units),
                created_by="system",
            )
            supplies_created.append(supply)

            for i in range(random.randint(1, 10)):
                initial_quantity = random.randint(10, 100)
                Batch.objects.create(
                    supply=supply,
                    batch_number=fake.unique.bothify(text="LOTE-####"),
                    expiry_date=fake.future_date(end_date="+1y"),
                    initial_quantity=initial_quantity,
                    current_quantity=initial_quantity,
                    unit_cost=random.uniform(1.0, 50.0),
                    status=Batch.StatusChoices.ACTIVE,
                    created_by="system",
                )

        self.stdout.write(
            self.style.SUCCESS(f"Successfully created {count} supplies and their batches.")
        )
