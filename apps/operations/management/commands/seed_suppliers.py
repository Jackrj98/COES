import random
import uuid

from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker

from apps.operations.models import Supplier
from apps.security.utils.utils import generate_ecuadorian_id


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--number", type=int, default=10)

    def handle(self, *args, **options):
        fake = Faker()
        count = options["number"]

        created_count = 0
        with transaction.atomic():
            for _ in range(count):
                try:
                    Supplier.objects.create(
                        business_name=fake.company().title(),
                        first_name=fake.first_name_male(),
                        last_name=fake.last_name_male(),
                        document_number=generate_ecuadorian_id(),
                        delivery_days=random.randint(5, 20),
                        email=f"{uuid.uuid4().hex[:6]}@{fake.domain_name()}",
                        is_active=random.choice([True, False]),
                        phone=fake.numerify(text="+5939########"),
                        address=fake.address(),
                        created_by="system",
                    )
                    created_count += 1
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Error creating supplier: {e}"))
                    if created_count > 0:
                        break  # Rollback transaction

        self.stdout.write(
            self.style.SUCCESS(f"{created_count} out of {count} suppliers created successfully")
        )
