import random

from django.core.management.base import BaseCommand

from apps.inventory.models import Batch, InventoryMovement


class Command(BaseCommand):
    help = "Generates mock inventory movements for existing batches"

    def add_arguments(self, parser):
        parser.add_argument("--number", type=int, default=20, help="Number of movements to create")

    def handle(self, *args, **options):
        batches = Batch.objects.all()
        if not batches.exists():
            self.stdout.write(self.style.ERROR("No batches found. Create batches first!"))
            return

        count = options["number"]

        for _ in range(count):
            batch = random.choice(batches)
            movement_type = random.choice(
                [
                    InventoryMovement.Type.INBOUND,
                    InventoryMovement.Type.OUTBOUND,
                    InventoryMovement.Type.ADJUSTMENT,
                ]
            )

            is_increment = None
            if movement_type == InventoryMovement.Type.ADJUSTMENT:
                is_increment = random.choice([True, False])

            InventoryMovement.objects.create(
                batch=batch,
                movement_type=movement_type,
                concept="Movimiento generado por seeder",
                quantity=random.randint(1, 10),
                observation="Prueba automatizada",
                is_increment=is_increment,
                created_by="system",
            )

        self.stdout.write(self.style.SUCCESS(f"Successfully generated {count} movements."))
