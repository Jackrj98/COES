import uuid
import re
from locust import task, between
from .base import BaseUser


class CatalogUser(BaseUser):
    wait_time = between(1, 3)

    def on_start(self):
        super().on_start()
        self.last_created_catalog_id = None
        self.last_created_item_id = None

    @task(2)
    def test_create_catalog(self):
        csrftoken = self.client.cookies.get("csrftoken")
        if not csrftoken:
            return

        unique_id = uuid.uuid4().hex[:8]
        payload = {
            "csrfmiddlewaretoken": csrftoken,
            "name": f"Catalog {unique_id}",
            "code": f"CAT-{unique_id}",
            "priority": 10,
            "description": "Catálogo de prueba generado por Locust",
            "is_active": "on",
        }

        response = self.client.post(
            "/catalogs/create/",
            data=payload,
            headers={"X-CSRFToken": csrftoken},
            allow_redirects=True,
        )

        if response.status_code in (200, 302):
            final_url = response.url
            if final_url:
                match = re.search(r"/([a-f0-9-]{8,36})/?$", final_url)
                if match:
                    self.last_created_catalog_id = match.group(1)

    @task(3)
    def test_list_catalogs(self):
        self.client.get("/catalogs/")

    @task(1)
    def test_get_catalog(self):
        if not self.last_created_catalog_id:
            return
        self.client.get(f"/catalogs/{self.last_created_catalog_id}/")
    
    @task(3)
    def test_register_items(self):
        if not self.last_created_catalog_id:
            return

        csrftoken = self.client.cookies.get("csrftoken")
        unique_id = uuid.uuid4().hex[:6]
        payload = {
            "csrfmiddlewaretoken": csrftoken,
            "catalog": self.last_created_catalog_id,
            "name": f"Item {unique_id}",
            "code": f"ITEM-{unique_id}",
            "description": "Item de prueba",
            "priority": 10,
            "is_active": "on",
        }
        with self.client.post(
            f"/catalogs/{self.last_created_catalog_id}/items/create/",
            data=payload,
            headers={"X-CSRFToken": csrftoken},
            catch_response=True,
        ) as response:
            if response.status_code in (200, 302):
                if response.history and response.history[0].url:
                    try:
                        self.last_created_item_id = (
                            response.history[0].url.strip("/").split("/")[-1]
                        )
                    except:
                        pass

    @task(2)
    def test_update_items(self):
        if not self.last_created_item_id or not self.last_created_catalog_id:
            return
        csrftoken = self.client.cookies.get("csrftoken")
        unique_id = uuid.uuid4().hex[:4]
        payload = {
            "csrfmiddlewaretoken": csrftoken,
            "name": f"Updated Item {unique_id}",
            "code": f"UPD-{unique_id}",
            "description": "Descripción actualizada por Locust",
            "priority": 20,
            "is_active": "on",
        }
        self.client.post(
            f"/catalogs/{self.last_created_catalog_id}/items/{self.last_created_item_id}/update/",
            data=payload,
            headers={"X-CSRFToken": csrftoken},
        )
