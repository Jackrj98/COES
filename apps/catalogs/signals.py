from django.apps import apps
from django.db.models.signals import post_migrate
from django.dispatch import receiver


@receiver(post_migrate)
def populate_catalogs_items(sender, **kwargs):
    if sender.name != "apps.catalogs":
        return

    Catalog = apps.get_model("catalogs", "Catalog")
    CatalogItem = apps.get_model("catalogs", "CatalogItem")

    catalogs_data = {
        Catalog.CatalogCodes.SUPPLY_CATEGORY: {
            "name": "Categorías de Insumos",
            "items": [
                {"name": "Medicamentos", "code": "meds", "extra": "MED"},
                {"name": "Material de curación", "code": "dressing", "extra": "MAT"},
                {"name": "Equipo médico", "code": "equipment", "extra": "EQU"},
                {"name": "Reactivos", "code": "reagents", "extra": "REA"},
            ],
        },
        Catalog.CatalogCodes.UNIT_OF_MEASURE: {
            "name": "Unidades de Medida",
            "items": [
                {"name": "Mililitros", "code": "ml", "extra": "ml"},
                {"name": "Litros", "code": "lt", "extra": "lt"},
                {"name": "Microlitros", "code": "ul", "extra": "ul"},
                {"name": "Gramo", "code": "gram", "extra": "gr"},
                {"name": "Miligramo", "code": "mg", "extra": "mg"},
                {"name": "Microgramo", "code": "mcg", "extra": "mcg"},
                {"name": "Kilogramo", "code": "kg", "extra": "kg"},
                {"name": "Unidad", "code": "unit", "extra": "und"},
                {"name": "Caja", "code": "box", "extra": "cj"},
                {"name": "Set", "code": "set", "extra": "set"},
                {"name": "Blíster", "code": "blister", "extra": "bl"},
                {"name": "Frasco", "code": "vial", "extra": "fr"},
                {"name": "Ampolla", "code": "ampoule", "extra": "amp"},
                {"name": "Tableta", "code": "tablet", "extra": "tab"},
                {"name": "Paquete", "code": "package", "extra": "pq"},
                {"name": "Galón", "code": "gallon", "extra": "gl"},
                {"name": "Pieza (Unidad)", "code": "piece", "extra": "pz"},
                {"name": "Caja x 10 unidades", "code": "box_10", "extra": "cj10"},
                {"name": "Caja x 50 unidades", "code": "box_50", "extra": "cj50"},
                {"name": "Jeringa", "code": "syringe", "extra": "jrg"},
                {"name": "Punta", "code": "tip", "extra": "pt"},
                {"name": "Frasco Gotero", "code": "dropper", "extra": "frg"},
                {"name": "Cápsula", "code": "capsule", "extra": "cap"},
                {"name": "Sobre", "code": "envelope", "extra": "sb"},
                {"name": "Tubo", "code": "tube", "extra": "tb"},
                {"name": "Milímetros", "code": "mm", "extra": "mm"},
            ],
        },
        Catalog.CatalogCodes.INBOUND_CONCEPT: {
            "name": "Conceptos de Entrada",
            "items": [
                {"name": "Compra Directa", "code": "direct_purchase", "extra": "ENT-CP"},
                {"name": "Devolución de Área", "code": "area_return", "extra": "ENT-DV"},
                {
                    "name": "Ajuste por Inventario",
                    "code": "inventory_adjustment_in",
                    "extra": "ENT-AJ",
                },
                {"name": "Donación", "code": "donation", "extra": "ENT-DN"},
            ],
        },
        Catalog.CatalogCodes.OUTBOUND_CONCEPT: {
            "name": "Conceptos de Salida",
            "items": [
                {"name": "Despacho a Planta", "code": "plant_dispatch", "extra": "SAL-DP"},
                {"name": "Merma/Daño", "code": "damage_loss", "extra": "SAL-MR"},
                {
                    "name": "Ajuste por Inventario",
                    "code": "inventory_adjustment_out",
                    "extra": "SAL-AJ",
                },
                {"name": "Salida por Vencimiento", "code": "expiry_loss", "extra": "SAL-VC"},
            ],
        },
    }

    for catalog_code, data in catalogs_data.items():
        catalog, _ = Catalog.objects.get_or_create(
            code=catalog_code, defaults={"name": data["name"], "code": f"{catalog_code.upper()}"}
        )
        for item_data in data["items"]:
            CatalogItem.objects.get_or_create(
                catalog=catalog,
                code=item_data["code"].upper(),
                defaults={"name": item_data["name"], "extra": item_data["extra"]},
            )
