# tests/performance/locustfile.py
from random import choice, randint
from locust import HttpUser, between, task

users = [("u1", "pass123"), ("u2", "secret7"), ("u3", "hunter8")]


class BeneTasksUser(HttpUser):
    wait_time = between(0.1, 0.5)

    def on_start(self):
        username, password = choice(users)

        # пробуем зарегистрироваться (если пользователь уже есть — получим 400)
        self.client.post(
            "/register",
            json={"username": username, "password": password},
            name="/register",
            catch_response=False,
        )

        # берём токен и валидируем ответ
        with self.client.post(
            "/token",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            name="/token",
            catch_response=True,
        ) as r:
            if r.status_code == 200 and "access_token" in r.json():
                token = r.json()["access_token"]
                self.headers = {"Authorization": f"Bearer {token}"}
            else:
                r.failure(f"Auth failed: {r.status_code} {r.text}")
                # опционально останавливаем тест:
                # self.environment.runner.quit()

    @task(3)
    def create_task(self):
        pr = randint(1, 5)
        self.client.post(
            "/tasks",
            json={
                "title": f"locust-{pr}",
                "description": "load-test",
                "priority": pr,
            },
            headers=self.headers,
            name="/tasks POST",
        )

    @task(2)
    def list_tasks(self):
        self.client.get("/tasks", headers=self.headers, name="/tasks GET")

    @task(1)
    def top_tasks(self):
        self.client.get(
            "/tasks/top/?n=5&all_priorities=true",
            headers=self.headers,
            name="/tasks/top",
        )
