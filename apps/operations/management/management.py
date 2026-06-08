import datetime

from django.db import transaction


class OrderNumberGenerator:
    @staticmethod
    def generate(model_class):
        prefix = getattr(model_class, "ORDER_PREFIX", None)
        if not prefix:
            raise ValueError(f"Define ORDER_PREFIX en {model_class.__name__}")

        year = datetime.date.today().year
        with transaction.atomic():
            last_order = (
                model_class.objects.filter(order_number__startswith=f"{prefix}-{year}-")
                .select_for_update()
                .order_by("-order_number")
                .first()
            )

            last_num = 0
            if last_order:
                last_num = int(last_order.order_number.split("-")[-1])

            new_num = last_num + 1
            return f"{prefix}-{year}-{new_num:04d}"
