import random
import uuid

from django.core.management.base import BaseCommand
from faker import Faker

from apps.operations.models import Supplier
from apps.security.utils.utils import generate_ecuadorian_id


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--number", type=int, default=10)

    def handle(self, *args, **options):
        fake = Faker()
        count = options["number"]

        Supplier.objects.bulk_create(
            [
                Supplier(
                    business_name=fake.company().title(),
                    contact_name=fake.first_name_male(),
                    tax_id=generate_ecuadorian_id(),
                    delivery_days=random.randint(5, 20),
                    email=f"{uuid.uuid4().hex[:6]}@{fake.domain_name()}",
                    is_active=random.choice([True, False]),
                    phone=fake.numerify(text="+5939########"),
                    address=fake.address(),
                    created_by="system",
                )
                for _ in range(count)
            ]
        )

        self.stdout.write(self.style.SUCCESS(f"{count} records have been successfully created."))
