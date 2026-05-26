import unicodedata

from apps.purchasing.models import Supplier


class SupplierBuilder:
    def __init__(self, supplier=None):
        self.supplier = supplier

    @staticmethod
    def _normalize_string(value: str) -> str:
        if not value:
            return ""
        normalized = unicodedata.normalize("NFKD", value).encode("ASCII", "ignore").decode("utf-8")
        return normalized.strip().lower()

    def create_supplier(self, business_name, reason, tax_id, delivery_days, email, phone):
        self.supplier = Supplier.objects.create(
            business_name=business_name.strip().title(),
            reason=reason.strip().title(),
            tax_id=tax_id.strip().upper(),
            delivery_days=int(delivery_days),
            email=email.lower(),
            phone=phone.strip(),
        )
        return self

    def update_supplier(self, business_name, reason, tax_id, delivery_days, email, phone):
        self.supplier.business_name = business_name.strip().title()
        self.supplier.reason = reason.strip().title()
        self.supplier.tax_id = tax_id.strip().upper()
        self.supplier.delivery_days = int(delivery_days)
        self.supplier.email = email.lower()
        self.supplier.phone = phone.strip()

        self.supplier.save(
            update_fields=["business_name", "reason", "tax_id", "delivery_days", "email", "phone"]
        )
        return self

    def change_status(self):
        current = self.supplier.is_active
        new_status = not current

        self.supplier.is_active = new_status
        self.supplier.save(update_fields=["is_active"])
        return self

    def build(self):
        return self.supplier
