from itertools import cycle
from locust import HttpUser, task, between

USERS = cycle([
    ("ahmed", "Ahmed123"),
    ("mohamed", "Mohamed123")
])

class ChatUser(HttpUser):
    wait_time = between(0.1, 0.5)

    def on_start(self):
        username, password = next(USERS)
        self.username = username

        response = self.client.post(
            "/auth/login",
            data={
                "username": username,
                "password": password,
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

        response.raise_for_status()
        self.token = response.json()["access_token"]

    @task
    def list_conversations(self):
        self.client.get(
            "/conversations/",
            headers={
                "Authorization": f"Bearer {self.token}",
            },
            name="/conversations/ per-user",
        )