from django.core.management.base import BaseCommand

from apps.catalogs.models import Catalog, CatalogItem


class Command(BaseCommand):
    help = "Generate required catalogs for Supply management"

    def handle(self, *args, **options):
        required_catalogs = [
            {
                "name": "Categoría de Insumos",
                "code": Catalog.CatalogCodes.SUPPLY_CATEGORY,
                "description": "Clasificación de insumos médicos/dentales",
            },
            {
                "name": "Unidad de Medida",
                "code": Catalog.CatalogCodes.UNIT_OF_MEASURE,
                "description": "Unidades de medida para el inventario",
            },
        ]

        for cat_data in required_catalogs:
            catalog, created = Catalog.objects.get_or_create(
                code=cat_data["code"],
                defaults={
                    "name": cat_data["name"],
                    "description": cat_data["description"],
                    "is_active": True,
                    "created_by": "system",
                },
            )

            items = []
            if catalog.code == Catalog.CatalogCodes.SUPPLY_CATEGORY:
                data = [("Instrumental", "INST"), ("Materiales", "MAT"), ("Equipos", "EQU")]
            else:
                data = [("Unidad", "UN"), ("Caja", "BOX"), ("Set", "SET"), ("Piezas", "PCS")]

            for name, code in data:
                items.append(
                    CatalogItem(
                        name=name,
                        code=f"{catalog.code}_{code}".upper(),
                        catalog=catalog,
                        is_active=True,
                        created_by="system",
                    )
                )

            CatalogItem.objects.bulk_create(items, ignore_conflicts=True)
            self.stdout.write(self.style.SUCCESS(f"Created catalog '{catalog.name}' and items."))
