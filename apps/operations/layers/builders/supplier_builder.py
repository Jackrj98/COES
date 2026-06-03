import unicodedata

from apps.operations.models import Supplier


class SupplierBuilder:
    def __init__(self, supplier=None):
        self.supplier = supplier or Supplier()

    @staticmethod
    def _normalize_string(value: str) -> str:
        if not value:
            return ""
        normalized = unicodedata.normalize("NFKD", value).encode("ASCII", "ignore").decode("utf-8")
        return normalized.strip().lower()

    def set_contact_name(self, name: str) -> "SupplierBuilder":
        self.supplier.contact_name = name.strip().capitalize()
        return self

    def set_email(self, email: str) -> "SupplierBuilder":
        self.supplier.email = self._normalize_string(email)
        return self

    def set_phone(self, phone: str) -> "SupplierBuilder":
        self.supplier.phone = phone.strip().replace(" ", "")
        return self

    def set_business_name(self, name: str) -> "SupplierBuilder":
        self.supplier.business_name = name.strip().title()
        return self

    def set_delivery_days(self, days: int) -> "SupplierBuilder":
        self.supplier.delivery_days = max(0, days)
        return self

    def set_tax_id(self, tax_id: str) -> "SupplierBuilder":
        self.supplier.tax_id = tax_id.strip().upper()
        return self

    def set_address(self, address: str) -> "SupplierBuilder":
        self.supplier.address = address.strip().capitalize()
        return self

    def save(self):
        self.supplier.save()
        return self

    def set_is_active(self, is_active: bool) -> "SupplierBuilder":
        self.supplier.is_active = not is_active
        return self

    def build(self):
        return self.supplier
