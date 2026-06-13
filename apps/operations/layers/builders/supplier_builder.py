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

    def set_first_name(self, first_name: str) -> "SupplierBuilder":
        if not first_name:
            raise ValueError("First name is required")
        self.supplier.first_name = self._normalize_string(first_name).title()
        return self

    def set_last_name(self, last_name: str) -> "SupplierBuilder":
        if not last_name:
            raise ValueError("Last name is required")
        self.supplier.last_name = self._normalize_string(last_name).title()
        return self

    def set_document_number(self, document_number: str) -> "SupplierBuilder":
        if not document_number:
            raise ValueError("Document is required")
        self.supplier.document_number = self._normalize_string(document_number)
        return self

    def set_email(self, email: str) -> "SupplierBuilder":
        if not email:
            raise ValueError("Email is required")
        self.supplier.email = self._normalize_string(email)
        return self

    def set_phone(self, phone: str) -> "SupplierBuilder":
        if not phone:
            raise ValueError("Phone is required")
        self.supplier.phone = phone.strip().replace(" ", "")
        return self

    def set_business_name(self, name: str) -> "SupplierBuilder":
        if not name:
            raise ValueError("Business name is required")
        self.supplier.business_name = name.strip().title()
        return self

    def set_delivery_days(self, days: int) -> "SupplierBuilder":
        self.supplier.delivery_days = max(0, days)
        return self

    def set_address(self, address: str) -> "SupplierBuilder":
        self.supplier.address = address.strip().capitalize()
        return self

    def set_is_active(self, is_active: bool) -> "SupplierBuilder":
        self.supplier.is_active = not is_active
        return self

    def build(self):
        self.supplier.full_clean()
        self.supplier.save()
        return self.supplier
