from test_locust.load.catalogs import CatalogUser  # noqa
from test_locust.load.base import BaseUser  # noqa

"""class CoesLoadTester(HttpUser):
wait_time = between(1, 3)

@task(3)
def test_operations(self):
self.client.get("/accounts/")
self.client.get("/inventory/movements/")
self.client.get("/operations/inbound/orders/")
self.client.get("/operations/outbound/orders/")

@task(2)
def test_inventory(self):
self.client.get("/inventory/supplies/")

@task(1)
def test_public_pages(self):
self.client.get("/")
self.client.get("/catalogs/")
self.client.get("/operations/suppliers/")

@task(1)
def test_security_auth(self):
self.client.get("/accounts/login/")
"""
