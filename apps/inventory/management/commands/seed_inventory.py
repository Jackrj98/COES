import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from faker import Faker

from apps.catalogs.models import Catalog, CatalogItem
from apps.inventory.models import Batch, InventoryMovement, Supply
from apps.operations.models import Supplier


class Command(BaseCommand):
    help = "Generates mock data for Supplies and Batches"

    ODONTO_ITEMS = [
        "Resina Compuesta",
        "Adhesivo Dental",
        "Ácido Grabador",
        "Alginato de Impresión",
        "Yeso Piedra",
        "Fresas de Diamante",
        "Guantes de Nitrilo",
        "Cubrebocas Tricapa",
        "Anestesia Lidocaína",
        "Hilo Retractor",
        "Cemento de Ionómero",
        "Puntas de Gutta Percha",
        "Puntas de Papel",
        "Solución Irrigante",
        "Microbrush",
        "Cera para Modelar",
        "Sutura de Seda",
        "Ápex Localizador",
    ]

    def add_arguments(self, parser):
        parser.add_argument("--number", type=int, default=10, help="Number of supplies to create")

    def handle(self, *args, **options):
        fake = Faker("es_ES")
        fake.unique.clear()
        count = options["number"]

        categories = list(
            CatalogItem.objects.filter(catalog__code=Catalog.CatalogCodes.SUPPLY_CATEGORY)
        )
        units = list(CatalogItem.objects.filter(catalog__code=Catalog.CatalogCodes.UNIT_OF_MEASURE))

        if not categories or not units:
            self.stdout.write(
                self.style.ERROR("Error: Ensure CatalogItems exist for categories and units first.")
            )
            return

        total_batches = 0
        supplier = Supplier.objects.first()
        for i in range(count):
            category = random.choice(categories)
            base_name = (
                random.choice(self.ODONTO_ITEMS)
                if i < len(self.ODONTO_ITEMS)
                else fake.unique.word().title()
            )
            name = f"{base_name} {fake.unique.random_int(min=1, max=999)}"
            max_quantity = random.randint(100, 500)
            supply = Supply.objects.create(
                name=name,
                code=fake.unique.bothify(text=f"{category.extra or 'SUP'}-####"),
                barcode=fake.unique.ean13(),
                description=fake.sentence(),
                stock_min=random.randint(5, 50),
                stock_max=max_quantity,
                category=category,
                unit_of_measure=random.choice(units),
                created_by="system",
            )

            current_total_stock = 0
            num_batches = random.randint(1, 5)
            for _ in range(num_batches):
                remaining_space = max_quantity - current_total_stock
                if remaining_space < 20:
                    break
                upper_bound = min(100, remaining_space)
                initial_quantity = random.randint(20, upper_bound)
                batch = Batch.objects.create(
                    supply=supply,
                    batch_number=fake.unique.bothify(text="LT-####"),
                    expiry_date=fake.future_date(end_date="+2y"),
                    initial_quantity=initial_quantity,
                    current_quantity=initial_quantity,
                    unit_cost=Decimal(str(round(random.uniform(1.0, 50.0), 2))),
                    status=Batch.BatchStatus.ACTIVE,
                    created_by="system",
                    supplier=supplier,
                )
                total_batches += 1
                current_total_stock += initial_quantity

                InventoryMovement.objects.create(
                    batch=batch,
                    movement_type=InventoryMovement.Type.INBOUND,
                    concept=f"Initial stock for batch {batch.batch_number}",
                    quantity=initial_quantity,
                    observation="Auto-generated inbound movement",
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
