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
                data = [
                    ("Instrumental", "INST", "INST"),
                    ("Materiales", "MAT", "MAT"),
                    ("Equipos", "EQU", "EQU"),
                    ("Medicamentos", "MED", "MED"),
                    ("Desechables", "DES", "DES"),
                ]
            else:  # UNIT_OF_MEASURE
                data = [
                    ("Unidad", "UN", "und"),
                    ("Caja", "BOX", "caja"),
                    ("Paquete", "PKG", "paq"),
                    ("Set", "SET", "set"),
                    ("Piezas", "PCS", "pza"),
                    ("Mililitro", "ML", "ml"),
                    ("Gramo", "GR", "g"),
                    ("Kilogramo", "KG", "kg"),
                    ("Litro", "L", "l"),
                ]

            for name, code, extra in data:
                items.append(
                    CatalogItem(
                        name=name,
                        code=f"{catalog.code}_{code}".upper(),
                        extra=extra,
                        catalog=catalog,
                        is_active=True,
                        created_by="system",
                    )
                )

            CatalogItem.objects.bulk_create(items, ignore_conflicts=True)

            status = "Created" if created else "Already existed"
            self.stdout.write(
                self.style.SUCCESS(f"{status} catalowg '{catalog.name}' with {len(items)} items.")
            )

            self.stdout.write(self.style.SUCCESS(f"Created catalog '{catalog.name}' and items."))
