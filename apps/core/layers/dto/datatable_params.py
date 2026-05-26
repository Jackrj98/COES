class DataTableParams:
    """Class for managing datatable filters via AJAX."""

    def __init__(self, request, **kwargs):
        """Initializes the instance with request parameters."""
        self.request = request
        self.kwargs = kwargs

        # Pagination and search
        self.draw = int(kwargs.get("draw", [0])[0])
        self.length = int(kwargs.get("length", [10])[0])
        self.start = int(kwargs.get("start", [0])[0])
        self.search_value = (kwargs.get("search[value]", [""])[0]).strip()

        # Ordering
        order_column_index = kwargs.get("order[0][column]", [None])[0]

        if order_column_index is not None:
            self.i_order_column = int(order_column_index)
            self.s_order_column = kwargs.get(f"columns[{self.i_order_column}][data]", ["id"])[0]
            self.t_order = kwargs.get("order[0][dir]", ["asc"])[0]

            prefix = "-" if self.t_order == "desc" else ""
            self.order_column = f"{prefix}{self.s_order_column}"
        else:
            # Default order: Newest first
            self.order_column = "-created_at"

    def get(self, key, default=None):
        """Get the value associated with the given key."""
        return self.kwargs.get(key, default)

    def get_array(self, key):
        """Get an array value from the kwargs."""
        value = self.get(key + "[]", [])
        if isinstance(value, str):
            return [value]
        return value

    def get_search_values(self):
        """Returns a list of search values."""
        return self.search_value.split(" ")

    def init_items(self, queryset):
        """Calculates total count, applies ordering, and paginates the QuerySet."""
        # Count before paginating so recordsFiltered is accurate
        self.count = queryset.count()

        # Apply ordering
        queryset = queryset.order_by(self.order_column)

        # Apply pagination
        self.items = queryset[self.start : self.start + self.length]

        return self.items

    def result(self, data: list):
        """Generates a result dictionary for DataTables."""
        return {
            "data": data,
            "draw": self.draw,
            "recordsTotal": self.total,
            "recordsFiltered": self.count,
        }
