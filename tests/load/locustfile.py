from locust import HttpUser, task, between, events
import random
import uuid  # Для более уникальных имен пользователей


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("Начинается новый тест Locust")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("Тест Locust завершается")


class TaskUser(HttpUser):
    wait_time = between(0.5, 2.5)  # Время ожидания между выполнениями задач
    token = None
    user_tasks_ids = []  # Храним ID задач, созданных этим пользователем

    def on_start(self):
        """Вызывается при старте пользователя Locust."""
        self.username = f"loaduser_{uuid.uuid4().hex[:8]}"  # Используем uuid для уникальности
        self.password = "loadtestpassword"

        # Регистрация
        reg_response = self.client.post("/register", json={"username": self.username, "password": self.password})
        if reg_response.status_code != 200 and reg_response.status_code != 400:  # 400 если пользователь существует
            print(f"Регистрация не удалась для {self.username}: {reg_response.status_code} - {reg_response.text}")

        # Вход
        login_response = self.client.post("/token", data={"username": self.username, "password": self.password})
        if login_response.status_code == 200:
            self.token = login_response.json()["access_token"]
        else:
            print(f"Вход не удался для {self.username}: {login_response.status_code} - {login_response.text}")
            self.token = None

    @task(10)  # Больший вес для создания задач
    def create_task(self):
        if not self.token:
            return
        headers = {"Authorization": f"Bearer {self.token}"}
        task_data = {
            "title": f"Задача {random.randint(1, 100000)} от {self.username}",
            "description": "Это задача, созданная во время нагрузочного тестирования.",
            "status": random.choice(["в ожидании", "в работе", "завершено"]),
            "priority": random.randint(0, 10)  # Более широкий диапазон приоритетов для тестирования
        }
        with self.client.post("/tasks", json=task_data, headers=headers, name="/tasks (POST создание)",
                              catch_response=True) as response:
            if response.status_code == 200:
                try:
                    task_id = response.json()["id"]
                    self.user_tasks_ids.append(task_id)
                    response.success()
                except (KeyError, TypeError):
                    response.failure("Не удалось извлечь ID задачи из успешного ответа на создание")
            else:
                response.failure(f"Создание задачи не удалось со статусом {response.status_code}")

    @task(5)  # Средний вес для получения всех задач
    def get_all_tasks(self):
        if not self.token:
            return
        headers = {"Authorization": f"Bearer {self.token}"}

        # 70% шанс отсутствия параметров (чтобы попасть в кэш, если он активен и другие параметры не используются пользователем)
        if random.random() < 0.7:
            self.client.get("/tasks", headers=headers, name="/tasks (GET все, без_параметров)")
        else:
            sort_options = ["title", "status", "created_at", "priority"]
            sort_by = random.choice(sort_options)
            order = random.choice(["asc", "desc"])
            search_term = random.choice(
                ["", "Задача", "load", f"{random.randint(1, 100)}"])  # Добавил случайное число в поиск
            url = f"/tasks?sort_by={sort_by}&order={order}"
            if search_term:
                url += f"&search={search_term}"
            self.client.get(url, headers=headers, name="/tasks (GET все, с_параметрами)")

    @task(3)  # Меньший вес для получения конкретной задачи
    def get_specific_task(self):
        if not self.token or not self.user_tasks_ids:
            # Если этот пользователь еще не создал задач, пытаемся сначала получить общие задачи для заполнения.
            # Это запасной вариант, в идеале user_tasks_ids должен содержать элементы из create_task.
            if not self.user_tasks_ids:
                headers = {"Authorization": f"Bearer {self.token}"}
                response = self.client.get("/tasks", headers=headers,
                                           name="/tasks (GET для_id_конкретной_задачи_фолбэк)")
                if response.status_code == 200:
                    try:
                        tasks = response.json()
                        if tasks:
                            self.user_tasks_ids = [t["id"] for t in tasks]
                    except Exception:
                        pass  # Игнорируем, если парсинг не удался

            if not self.user_tasks_ids:  # Все еще нет задач
                return

        headers = {"Authorization": f"Bearer {self.token}"}
        task_id_to_get = random.choice(self.user_tasks_ids)
        self.client.get(f"/tasks/{task_id_to_get}", headers=headers, name="/tasks/{id} (GET конкретная)")

    @task(2)
    def get_top_tasks(self):
        if not self.token:
            return
        headers = {"Authorization": f"Bearer {self.token}"}
        n = random.randint(3, 7)

        rand_val = random.random()
        if rand_val < 0.33:  # Конкретный приоритет
            prio = random.randint(0, 10)
            self.client.get(f"/tasks/top/?n={n}&priority={prio}", headers=headers,
                            name="/tasks/top (GET, конкретный_приоритет)")
        elif rand_val < 0.66:  # Все приоритеты
            self.client.get(f"/tasks/top/?n={n}&all_priorities=true", headers=headers,
                            name="/tasks/top (GET, все_приоритеты)")
        else:  # Топ по умолчанию
            self.client.get(f"/tasks/top/?n={n}", headers=headers, name="/tasks/top (GET, топ_по_умолчанию)")

    @task(1)
    def update_random_task(self):
        if not self.token or not self.user_tasks_ids:
            return

        headers = {"Authorization": f"Bearer {self.token}"}
        task_id_to_update = random.choice(self.user_tasks_ids)
        update_payload = {
            "title": f"Обновленный Заголовок Задачи {uuid.uuid4().hex[:6]}",
            "status": random.choice(["в ожидании", "в работе", "завершено"]),
            "priority": random.randint(0, 10)
        }
        self.client.put(f"/tasks/{task_id_to_update}", json=update_payload, headers=headers,
                        name="/tasks/{id} (PUT обновление)")

    # Удаление задач может привести к сбою других задач, если они зависят от ID задач.
    # @task(1)
    # def delete_random_task(self):
    #     if not self.token or not self.user_tasks_ids:
    #         return

    #     headers = {"Authorization": f"Bearer {self.token}"}
    #     task_id_to_delete = random.choice(self.user_tasks_ids)

    #     with self.client.delete(f"/tasks/{task_id_to_delete}", headers=headers, name="/tasks/{id} (DELETE)", catch_response=True) as response:
    #         if response.status_code == 200:
    #             try:
    #                 self.user_tasks_ids.remove(task_id_to_delete)
    #                 response.success()
    #             except ValueError: # ID уже удален
    #                 response.success() # Все равно успех с точки зрения API
    #         elif response.status_code == 404: # Уже удалено другим пользователем/процессом
    #             try:
    #                 self.user_tasks_ids.remove(task_id_to_delete)
    #             except ValueError:
    #                 pass
    #             response.success() # Считаем успехом для потока нагрузочного теста
    #         else:
    #             response.failure(f"Удаление задачи не удалось со статусом {response.status_code}")