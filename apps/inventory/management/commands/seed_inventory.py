# management/commands/generate_supplies.py

import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from faker import Faker

from apps.catalogs.models import Catalog, CatalogItem
from apps.inventory.models import Batch, InventoryMovement, Supply


class Command(BaseCommand):
    help = "Generates mock data for Supplies and Batches"

    def add_arguments(self, parser):
        parser.add_argument("--number", type=int, default=10, help="Number of supplies to create")

    def handle(self, *args, **options):
        fake = Faker("es_ES")
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
        total_batches = 0

        for _ in range(count):
            category = random.choice(categories)
            supply = Supply.objects.create(
                name=fake.unique.word().title(),
                code=fake.unique.bothify(text=f"{category.extra or 'SUP'}-####"),
                description=fake.sentence(),
                stock_min=random.randint(5, 50),
                category=category,
                unit_of_measure=random.choice(units),
                created_by="system",
            )
            supplies_created.append(supply)

            # Crear entre 1 y 5 batches por suministro
            num_batches = random.randint(1, 5)
            for i in range(num_batches):
                initial_quantity = random.randint(10, 100)

                # Crear batch
                batch = Batch.objects.create(
                    supply=supply,
                    batch_number=fake.unique.bothify(text="LOTE-####"),
                    expiry_date=fake.future_date(end_date="+2y"),
                    initial_quantity=initial_quantity,
                    current_quantity=initial_quantity,
                    unit_cost=Decimal(str(round(random.uniform(1.0, 50.0), 2))),
                    status=Batch.BatchStatus.ACTIVE,
                    created_by="system",
                )
                total_batches += 1

                # ✅ Registrar movimiento de ingreso (INBOUND) para el batch creado
                InventoryMovement.objects.create(
                    batch=batch,
                    movement_type=InventoryMovement.Type.INBOUND,
                    concept=f"Initial stock for batch {batch.batch_number}",
                    quantity=initial_quantity,
                    observation="Auto-generated inbound movement for batch creation",
                    previous_stock=0,
                    after_stock=initial_quantity,
                    is_increment=True,
                    unit_cost_at_movement=batch.unit_cost,
                    status=InventoryMovement.MovementStatusChoices.COMPLETED,
                    created_by="system",
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {count} supplies, {total_batches} batches, "
                f"and {total_batches} inbound movements."
            )
        )
