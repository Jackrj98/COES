import random
import uuid

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from faker import Faker

from apps.security.models import Person, User
from apps.security.utils.utils import generate_ecuadorian_id


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--number", type=int, default=10)

    def handle(self, *args, **options):
        fake = Faker()
        count = options["number"]
        group_names = ["specialist", "administrator"]
        groups = list(Group.objects.filter(name__in=group_names))

        # 1. Bulk create persons
        persons = Person.objects.bulk_create(
            [
                Person(
                    first_name=f"{fake.first_name()} {fake.first_name()}",
                    last_name=f"{fake.last_name()} {fake.last_name()}",
                    document_number=generate_ecuadorian_id(),
                    phone=fake.numerify(text="+5939########"),
                )
                for _ in range(count)
            ]
        )

        # 2. Bulk create users
        users = User.objects.bulk_create(
            [
                User(
                    username=person.document_number,
                    email=f"{uuid.uuid4().hex[:6]}_{fake.email()}",
                    password=make_password(person.document_number),
                    person=person,
                    is_active=random.choice([True, False]),
                    status=random.choice([1, 2, 3]),
                )
                for person in persons
            ]
        )

        # 3. Bulk assign groups (M2M)
        UserGroups = User.groups.through
        UserGroups.objects.bulk_create(
            [UserGroups(user=user, group=random.choice(groups)) for user in users]
        )

        self.stdout.write(self.style.SUCCESS(f"{count} records have been successfully created."))
