import random
import uuid

from django.core.management.base import BaseCommand
from faker import Faker

from apps.security.layers.applications import UserAppService
from apps.security.utils.utils import generate_ecuadorian_id


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--number", type=int, default=10)

    def handle(self, *args, **options):
        fake = Faker()
        count = options["number"]
        service = UserAppService()
        groups = ["specialist", "administrator"]

        for _ in range(count):
            unique_suffix = uuid.uuid4().hex[:6]
            raw_document_number = generate_ecuadorian_id()

            service.register_user(
                payload={
                    "username": raw_document_number,
                    "email": f"{unique_suffix}_{fake.email()}",
                    "password": raw_document_number,
                    "first_name": fake.first_name(),
                    "last_name": fake.last_name(),
                    "document_number": raw_document_number,
                    "phone": fake.numerify(text="+5939########"),
                    "groups": [random.choice(groups)],
                }
            )

        self.stdout.write(self.style.SUCCESS(f"{count} records have been successfully created."))
