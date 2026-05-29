import random

from django.core.management.base import BaseCommand

from apps.catalogs.models import Catalog, CatalogItem


class Command(BaseCommand):
    help = "Generate medical and dental catalogs"

    # Predefined catalogs
    CATALOGS = [
        {
            "name": "Instrumental Quirúrgico Dental",
            "code": "dent_surgical_instruments",
            "description": "Instrumentos quirúrgicos para procedimientos dentales",
        },
        {
            "name": "Materiales de Endodoncia",
            "code": "endo_materials",
            "description": "Limas, conos de gutapercha y selladores endodónticos",
        },
        {
            "name": "Ortodoncia",
            "code": "ortho_supplies",
            "description": "Brackets, arcos, ligas y bandas ortodóncicas",
        },
        {
            "name": "Prótesis Dental",
            "code": "prostho_materials",
            "description": "Materiales para prótesis fija y removible",
        },
        {
            "name": "Equipos de Diagnóstico",
            "code": "diagnostic_equipment",
            "description": "Rayos X, scanner intraoral, cámaras",
        },
        {
            "name": "Implantes Dentales",
            "code": "dental_implants",
            "description": "Implantes, pilares y componentes protésicos",
        },
        {
            "name": "Materiales de Bioseguridad",
            "code": "biosecurity",
            "description": "Guantes, mascarillas, batas y protectores",
        },
        {
            "name": "Farmacia Dental",
            "code": "dental_pharmacy",
            "description": "Anestésicos, antibióticos y antiinflamatorios",
        },
        {
            "name": "Laboratorio Dental",
            "code": "dental_lab",
            "description": "Materiales de laboratorio y equipos",
        },
        {
            "name": "Instrumental Médico General",
            "code": "medical_instruments",
            "description": "Instrumental médico para consulta general",
        },
    ]

    def handle(self, *args, **options):
        # Create catalogs
        catalogs = []
        for i, catalog_data in enumerate(self.CATALOGS, 1):
            catalog = Catalog(
                name=catalog_data["name"],
                code=catalog_data["code"].upper(),
                description=catalog_data["description"],
                priority=i * 10,
                is_active=True,
                created_by="system",
            )
            catalogs.append(catalog)

        created_catalogs = Catalog.objects.bulk_create(catalogs)

        # Create items for each catalog
        items = []
        for catalog in created_catalogs:
            items.extend(self.create_items_for_catalog(catalog))

        CatalogItem.objects.bulk_create(items)

        self.stdout.write(
            self.style.SUCCESS(f"Created {len(created_catalogs)} catalogs and {len(items)} items")
        )

    def create_items_for_catalog(self, catalog):
        """Create items specific to each catalog."""
        items_data = {
            "dent_surgical_instruments": [
                ("Bisturí Dental", "DENT_SURG_001"),
                ("Pinza Kelly", "DENT_SURG_002"),
                ("Porta Agujas", "DENT_SURG_003"),
                ("Separador de Minnesota", "DENT_SURG_004"),
                ("Cucharilla de Legrado", "DENT_SURG_005"),
            ],
            "endo_materials": [
                ("Lima K #15", "ENDO_001"),
                ("Lima Hedstrom #20", "ENDO_002"),
                ("Cono de Gutapercha", "ENDO_003"),
                ("Sellador Endodóntico", "ENDO_004"),
                ("Hidróxido de Calcio", "ENDO_005"),
            ],
            "ortho_supplies": [
                ("Bracket Metálico", "ORTHO_001"),
                ("Arco NiTi .016", "ORTHO_002"),
                ("Liga Elástica", "ORTHO_003"),
                ("Banda Molar", "ORTHO_004"),
                ("Resina de Brackets", "ORTHO_005"),
            ],
        }

        items = []
        default_items = [
            ("Artículo Estándar 1", "STD_001"),
            ("Artículo Estándar 2", "STD_002"),
            ("Artículo Estándar 3", "STD_003"),
        ]

        catalog_items = items_data.get(catalog.code, default_items)

        for i, (name, code) in enumerate(catalog_items, 1):
            item = CatalogItem(
                name=name,
                code=f"{catalog.code}_{code}".upper(),
                priority=i * 10,
                extra=random.choice(["UN", "BOX", "SET", "PCS"]),
                catalog=catalog,
                is_active=True,
                created_by="system",
            )
            items.append(item)

        return items
