class DataTableParams:
    """Class for managing datatable filters via AJAX."""

    # Filters
    draw = 0  # Contador utilizado por datatable (retorna el mismo valor que llega)
    start = 0  # Inicio de página
    length = 0  # Items por página
    search_value = ""  # Texto a filtrar

    # Order
    i_order_column = 0  # Número de columna por la cual se debe ordenar
    s_order_column = "id"  # Nombre de columna a ordenar
    t_order = "asc"  # Tipo de ordenación: asc, desc
    order_column = ""  # Ordenación en ORM de DJango

    # Data
    total = 0  # Total de registros
    count = 0  # Número de registro que coinciden con los filtros
    items = []  # Lista de datos a mostrar (Sin aplicar formatos)
    data = []  # Lista de datos formateados

    kwargs = []

    # parameterized constructor with request.POST
    def __init__(self, request, **kwargs):
        """Initializes an instance of the class.

        Parameters:
            request (type): The request object.
            **kwargs (type): Additional keyword arguments.
        """
        self.kwargs = kwargs

        self.draw = int(kwargs.get("draw", [0])[0])
        self.length = int(kwargs.get("length", [10])[0])
        self.start = int(kwargs.get("start", [0])[0])
        self.search_value = (kwargs.get("search[value]", [""])[0]).strip()

        self.i_order_column = kwargs.get("order[0][column]", [0])[0]
        self.s_order_column = kwargs.get(f"columns[{self.i_order_column}][data]", ["id"])[0]

        self.t_order = kwargs.get("order[0][dir]", ["desc"])[0]

        if self.t_order == "desc":
            self.order_column = "-" + self.s_order_column
        else:
            self.order_column = self.s_order_column
        self.request = request

    def get(self, key, default=None):
        """Get the value associated with the given key from the dictionary.

        Args:
            key (Any): The key to search for in the dictionary.
            default (Any, optional): The default value to return if the key is not found.

        Returns:
            Any: The value associated with the key, or the default value if the key is not found.
        """
        return self.kwargs.get(key, default)

    def get_array(self, key):
        """Get an array value from the dictionary based on a given key.

        Args:
            key (str): The key to retrieve the array value from the dictionary.

        Returns:
            list: The array value associated with the given key. If the key does not exist, an empty list is returned.

        """
        value = self.get(key + "[]", [])
        if isinstance(value, str):
            return [value]
        return value

    def get_search_values(self):
        """Returns a list of search values.

        Returns:
            list: A list of search values.
        """
        return self.search_value.split(" ")

    def init_items(self, queryset):
        """Initializes the items attribute of the class with a subset of the given queryset.

        Parameters:
            queryset (QuerySet): The queryset containing the items.

        Returns:
            QuerySet: The subset of the queryset ordered by the order_column attribute
            and sliced from start to start + length.
        """
        self.items = queryset.order_by(self.order_column)[self.start : self.start + self.length]
        return self.items

    def result(self, data: list):
        """Generate a result dictionary based on the given data.

        Args:
            data (list): The list of data to be included in the result. Defaults to an empty list.

        Returns:
            dict: A dictionary containing the generated result.
        """
        r = dict()

        if data:
            self.data = data

        r["data"] = self.data
        r["draw"] = self.draw
        r["recordsTotal"] = self.total
        r["recordsFiltered"] = self.count
        return r
