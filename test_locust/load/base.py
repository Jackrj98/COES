from locust import HttpUser, between


class BaseUser(HttpUser):
    abstract = True
    wait_time = between(1, 3)

    def on_start(self):
        self.client.get("/accounts/login/")

        self.client.post(
            "/accounts/login/",
            {
                "username": "develop",
                "password": "develop",
                "csrfmiddlewaretoken": self.client.cookies.get("csrftoken"),
            },
        )
