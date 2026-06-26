from apps.security.models import Person


class PersonBuilder:
    def __init__(self, person=None):
        self.person = person or Person()

    @staticmethod
    def _normalize_text(value: str) -> str:
        """Helper method to normalize text."""
        if not value:
            return ""
        return value.strip().title()

    def set_first_name(self, first_name: str) -> "PersonBuilder":
        self.person.first_name = self._normalize_text(first_name)
        return self

    def set_last_name(self, last_name: str) -> "PersonBuilder":
        self.person.last_name = self._normalize_text(last_name)
        return self

    def set_document_number(self, document_number: str) -> "PersonBuilder":
        """Cleave the document number and set it to the person."""
        self.person.document_number = document_number.strip().upper()
        return self

    def set_phone(self, phone: str) -> "PersonBuilder":
        self.person.phone = phone.strip()
        return self

    def build(self) -> Person:
        # self.person.full_clean()
        self.person.save()
        return self.person
