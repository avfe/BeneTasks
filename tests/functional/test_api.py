import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import time

# Предполагается, что они импортированы из вашего основного файла приложения (например, main.py)
import main as main_module  # Для доступа к main_module.cache_data и т.д.
from main import User, Task  # Для подсказок типов и прямых проверок в БД


class TestAuth:
    def test_register_new_user(self, client: TestClient, test_user_data_factory):
        user_data = test_user_data_factory()
        response = client.post("/register", json=user_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_register_existing_user(self, client: TestClient, created_test_user: User, test_user_data: dict):
        # created_test_user по умолчанию использует test_user_data.
        response = client.post("/register",
                               json={"username": test_user_data["username"], "password": "anotherpassword"})
        assert response.status_code == 400
        assert response.json()["detail"] == "Пользователь уже существует"

    def test_login_correct_credentials(self, client: TestClient, created_test_user: User, test_user_data: dict):
        response = client.post("/token",
                               data={"username": test_user_data["username"], "password": test_user_data["password"]})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_incorrect_password(self, client: TestClient, created_test_user: User, test_user_data: dict):
        response = client.post("/token", data={"username": test_user_data["username"], "password": "wrongpassword"})
        assert response.status_code == 400
        assert response.json()["detail"] == "Неверные имя пользователя или пароль"

    def test_login_nonexistent_user(self, client: TestClient):
        response = client.post("/token", data={"username": "nosuchuser", "password": "password"})
        assert response.status_code == 400
        assert response.json()["detail"] == "Неверные имя пользователя или пароль"

    def test_get_current_user_invalid_token_format(self, client: TestClient):
        response = client.get("/tasks", headers={"Authorization": "Bearer invalidtoken"})
        assert response.status_code == 401
        json_response = response.json()
        assert "Неверный токен" in json_response["detail"]

    def test_get_current_user_nonexistent_user_in_token(self, client: TestClient, db_session: Session,
                                                        test_user_data_factory):
        user_data = test_user_data_factory()
        # Регистрируем пользователя
        reg_response = client.post("/register", json=user_data)
        assert reg_response.status_code == 200

        # Входим, чтобы получить токен
        login_resp = client.post("/token", data=user_data)
        assert login_resp.status_code == 200
        temp_token = login_resp.json()["access_token"]

        # Удаляем пользователя из БД напрямую
        user_obj = db_session.query(User).filter(User.username == user_data["username"]).first()
        assert user_obj is not None
        db_session.delete(user_obj)
        db_session.commit()

        # Теперь пытаемся использовать токен
        response = client.get("/tasks", headers={"Authorization": f"Bearer {temp_token}"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Пользователь не найден"


class TestTasksCRUD:
    TASK_DATA_DEFAULT = {"title": "Задача по умолчанию", "description": "Описание по умолчанию", "status": "в ожидании",
                         "priority": 1}

    def test_create_task(self, client: TestClient, auth_headers: dict, db_session: Session, created_test_user: User):
        response = client.post("/tasks", json=self.TASK_DATA_DEFAULT, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == self.TASK_DATA_DEFAULT["title"]

        task_in_db = db_session.query(Task).filter(Task.id == data["id"]).first()
        assert task_in_db is not None
        assert task_in_db.title == self.TASK_DATA_DEFAULT["title"]
        assert task_in_db.owner_id == created_test_user.id

    def test_create_task_unauthenticated(self, client: TestClient):
        response = client.post("/tasks", json=self.TASK_DATA_DEFAULT)
        assert response.status_code == 401  # OAuth2PasswordBearer возвращает 401, если нет токена

    def test_get_tasks_for_user(self, client: TestClient, auth_headers: dict, create_task_for_user):
        create_task_for_user(title="Моя задача 1", description="О1", status="в работе", priority=2)
        create_task_for_user(title="Моя задача 2", description="О2", status="завершено", priority=0)

        response = client.get("/tasks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        titles = {t["title"] for t in data}
        assert "Моя задача 1" in titles
        assert "Моя задача 2" in titles

    def test_get_tasks_unauthenticated(self, client: TestClient):
        response = client.get("/tasks")
        assert response.status_code == 401

    def test_get_task_by_id(self, client: TestClient, auth_headers: dict, create_task_for_user):
        task = create_task_for_user(title="Конкретная задача", description="К Описание", status="в ожидании",
                                    priority=5)

        response = client.get(f"/tasks/{task.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task.id
        assert data["title"] == "Конкретная задача"

    def test_get_task_by_id_not_found(self, client: TestClient, auth_headers: dict):
        response = client.get("/tasks/99999", headers=auth_headers)
        assert response.status_code == 404
        assert response.json()["detail"] == "Задача не найдена"

    def test_get_task_by_id_not_owned(self, client: TestClient, admin_auth_headers: dict, create_task_for_user):
        # Задача создана 'created_test_user' (через create_task_for_user, который использует его контекст)
        task = create_task_for_user(title="Задача пользователя", description="Польз. Описание", status="в ожидании",
                                    priority=1)

        # Администратор пытается ее получить. Эндпоинт фильтрует по owner_id == current_user.id
        response = client.get(f"/tasks/{task.id}", headers=admin_auth_headers)
        assert response.status_code == 404
        assert response.json()["detail"] == "Задача не найдена"

    def test_update_task(self, client: TestClient, auth_headers: dict, db_session: Session, create_task_for_user):
        task_obj = create_task_for_user(title="Старый заголовок", description="Старое описание", status="в ожидании",
                                        priority=1)

        update_data = {"title": "Новый заголовок", "status": "в работе", "priority": 10}
        response = client.put(f"/tasks/{task_obj.id}", json=update_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Новый заголовок"
        assert data["status"] == "в работе"
        assert data["priority"] == 10
        assert data["description"] == "Старое описание"  # Не изменено

        db_session.refresh(task_obj)
        assert task_obj.title == "Новый заголовок"
        assert task_obj.status == "в работе"
        assert task_obj.priority == 10

    def test_update_task_partial(self, client: TestClient, auth_headers: dict, db_session: Session,
                                 create_task_for_user):
        task_obj = create_task_for_user(title="Частичное обновление", description="Описание", status="в ожидании",
                                        priority=1)
        update_data = {"title": "Частично новый заголовок"}  # Только заголовок
        response = client.put(f"/tasks/{task_obj.id}", json=update_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Частично новый заголовок"
        assert data["status"] == "в ожидании"  # Не изменено

    def test_update_task_not_found(self, client: TestClient, auth_headers: dict):
        update_data = {"title": "Новый заголовок"}
        response = client.put("/tasks/99999", json=update_data, headers=auth_headers)
        assert response.status_code == 404

    def test_delete_task(self, client: TestClient, auth_headers: dict, db_session: Session, create_task_for_user):
        task_obj = create_task_for_user(title="К удалению", description="Удал. Описание", status="в ожидании",
                                        priority=1)
        task_id = task_obj.id

        response = client.delete(f"/tasks/{task_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["detail"] == "Задача удалена"

        deleted_task = db_session.query(Task).filter(Task.id == task_id).first()
        assert deleted_task is None

    def test_delete_task_not_found(self, client: TestClient, auth_headers: dict):
        response = client.delete("/tasks/99999", headers=auth_headers)
        assert response.status_code == 404


class TestTasksAdvancedGet:
    @pytest.fixture(autouse=True)
    def setup_tasks(self, create_task_for_user):
        # Общие задачи для тестов сортировки/поиска/кэширования/топа
        self.task_c = create_task_for_user(title="Задача В", description="Описание В", status="в ожидании", priority=1,
                                           created_at=datetime(2023, 1, 1, 10, 0, 0))
        self.task_a = create_task_for_user(title="Задача А", description="Описание А (яблоко)", status="в работе",
                                           priority=3, created_at=datetime(2023, 1, 1, 12, 0, 0))
        self.task_b = create_task_for_user(title="Задача Б", description="Описание Б", status="завершено", priority=2,
                                           created_at=datetime(2023, 1, 1, 11, 0, 0))
        # Для топ-задач добавим больше разнообразия
        self.task_p5_new = create_task_for_user(title="П5 Задача Новая", description="О", status="с", priority=5,
                                                created_at=datetime(2023, 1, 1, 14, 0, 0))
        self.task_p5_old = create_task_for_user(title="П5 Задача Старая", description="О", status="с", priority=5,
                                                created_at=datetime(2023, 1, 1, 9, 0, 0))
        self.task_p0_new = create_task_for_user(title="П0 Задача Новая", description="О", status="с", priority=0,
                                                created_at=datetime(2023, 1, 1, 15, 0, 0))  # Самая новая в целом
        self.task_p0_old = create_task_for_user(title="П0 Задача Старая", description="О", status="с", priority=0,
                                                created_at=datetime(2023, 1, 1, 8, 0, 0))  # Самая старая П0

        # Ожидаемые все задачи для текущего пользователя (7 задач)
        # Этот список не используется напрямую, но полезен для понимания набора данных.

    def test_get_tasks_sorting(self, client: TestClient, auth_headers: dict):
        # Сортировка по заголовку asc
        response = client.get("/tasks?sort_by=title&order=asc", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 7  # Всего задач для этого пользователя
        # 'Задача А', 'Задача Б', 'Задача В', 'П0 Задача Новая', 'П0 Задача Старая', 'П5 Задача Новая', 'П5 Задача Старая'
        expected_sorted_titles = sorted(
            [self.task_a.title, self.task_b.title, self.task_c.title, self.task_p0_new.title, self.task_p0_old.title,
             self.task_p5_new.title, self.task_p5_old.title])
        assert [t["title"] for t in data] == expected_sorted_titles

        # Сортировка по приоритету desc
        response = client.get("/tasks?sort_by=priority&order=desc", headers=auth_headers)
        data = response.json()
        # Вторичная сортировка не гарантируется только этим запросом, поэтому просто проверяем, что приоритеты убывают
        priorities = [t["priority"] for t in data]
        assert all(priorities[i] >= priorities[i + 1] for i in range(len(priorities) - 1))
        assert sorted(priorities, reverse=True) == priorities  # Проверяем, полностью ли отсортировано по приоритету

        # Сортировка по created_at asc
        response = client.get("/tasks?sort_by=created_at&order=asc", headers=auth_headers)
        data = response.json()
        created_ats = [datetime.fromisoformat(t["created_at"]) for t in data]
        assert all(created_ats[i] <= created_ats[i + 1] for i in range(len(created_ats) - 1))

        # Неверный sort_by
        response = client.get("/tasks?sort_by=invalid_field&order=asc", headers=auth_headers)
        assert response.status_code == 400
        assert "Неверный параметр сортировки" in response.json()["detail"]

    def test_get_tasks_search(self, client: TestClient, auth_headers: dict):
        response = client.get("/tasks?search=яблоко", headers=auth_headers)  # Из описания 'task_a'
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == self.task_a.title

        response = client.get("/tasks?search=Описание В", headers=auth_headers)  # Из описания 'task_c'
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == self.task_c.title

        response = client.get("/tasks?search=несуществующий", headers=auth_headers)
        data = response.json()
        assert len(data) == 0

    def test_get_tasks_caching(self, client: TestClient, auth_headers: dict, monkeypatch, create_task_for_user):
        # Примечание: self.setup_tasks уже создал задачи. Тестируем с ними.
        # Кэш очищается после каждого теста фикстурой db_setup_and_teardown в conftest.py.
        assert main_module.cache_data["tasks"] is None

        # 1. Первый GET /tasks (без параметров) - должен заполнить кэш
        response1 = client.get("/tasks", headers=auth_headers)
        assert response1.status_code == 200
        tasks_from_response1 = response1.json()
        assert len(tasks_from_response1) == 7  # Из setup_tasks
        assert main_module.cache_data["tasks"] is not None
        # Кэш хранит ORM объекты
        assert len(main_module.cache_data["tasks"]) == 7

        # 2. Мокаем время, чтобы оно было в пределах CACHE_TIMEOUT
        current_time = time.time()
        monkeypatch.setattr(time, "time", lambda: current_time + main_module.CACHE_TIMEOUT / 2)
        original_cache_timestamp = main_module.cache_data["timestamp"]

        # 3. Второй GET /tasks (без параметров) - должен использовать кэш
        response2 = client.get("/tasks", headers=auth_headers)
        assert response2.status_code == 200
        # Сравниваем JSON ответы, так как они являются сравнимыми словарями
        assert response2.json() == tasks_from_response1
        assert main_module.cache_data["timestamp"] == original_cache_timestamp  # Временная метка не изменилась

        # 4. Мокаем время, чтобы оно было после CACHE_TIMEOUT
        monkeypatch.setattr(time, "time", lambda: current_time + main_module.CACHE_TIMEOUT + 5)

        # 5. Третий GET /tasks (без параметров) - должен получить свежие данные и обновить кэш
        response3 = client.get("/tasks", headers=auth_headers)
        assert response3.status_code == 200
        assert response3.json() == tasks_from_response1  # Данные все еще те же, так как БД не изменилась
        assert main_module.cache_data["timestamp"] > original_cache_timestamp  # Временная метка обновлена

        # 6. Создаем новую задачу (должно очистить кэш через clear_cache() в эндпоинте)
        new_task_data = {"title": "Задача для сброса кэша", "description": "...", "status": "...", "priority": 0}
        post_response = client.post("/tasks", json=new_task_data, headers=auth_headers)
        assert post_response.status_code == 200
        assert main_module.cache_data["tasks"] is None  # Кэш очищен

        # 7. GET /tasks снова - должен получить свежие данные (теперь 8 задач)
        response4 = client.get("/tasks", headers=auth_headers)
        assert response4.status_code == 200
        assert len(response4.json()) == 8  # 7 из setup + 1 новая
        assert main_module.cache_data["tasks"] is not None  # Кэш снова заполнен

    def test_get_top_tasks_default_n5(self, client: TestClient, auth_headers: dict):
        # Используются задачи из self.setup_tasks (7 задач)
        # По умолчанию: n=5, сначала самый высокий приоритет, затем по created_at desc
        response = client.get("/tasks/top/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5
        # Ожидается: П5 Задача Новая (п5, новая), П5 Задача Старая (п5, старая), Задача А (п3), Задача Б (п2), Задача В (п1)
        expected_titles = [self.task_p5_new.title, self.task_p5_old.title, self.task_a.title, self.task_b.title,
                           self.task_c.title]
        assert [t["title"] for t in data] == expected_titles
        assert [t["priority"] for t in data] == [5, 5, 3, 2, 1]

    def test_get_top_tasks_with_n_param(self, client: TestClient, auth_headers: dict):
        response = client.get("/tasks/top/?n=3", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        expected_titles = [self.task_p5_new.title, self.task_p5_old.title, self.task_a.title]
        assert [t["title"] for t in data] == expected_titles

    def test_get_top_tasks_specific_priority(self, client: TestClient, auth_headers: dict):
        # Получить топ N (по умолчанию 5) с приоритетом 5, отсортированных по created_at desc
        response = client.get("/tasks/top/?priority=5", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # Две задачи П5: П5 Задача Новая, П5 Задача Старая
        assert {t["title"] for t in data} == {self.task_p5_new.title, self.task_p5_old.title}
        assert data[0]["title"] == self.task_p5_new.title  # Самая новая П5 первая
        assert data[1]["title"] == self.task_p5_old.title

        # Получить топ N с приоритетом 0
        response_p0 = client.get("/tasks/top/?priority=0", headers=auth_headers)
        assert response_p0.status_code == 200
        data_p0 = response_p0.json()
        assert len(data_p0) == 2
        assert {t["title"] for t in data_p0} == {self.task_p0_new.title, self.task_p0_old.title}
        assert data_p0[0]["title"] == self.task_p0_new.title  # Самая новая П0 первая

    def test_get_top_tasks_all_priorities(self, client: TestClient, auth_headers: dict):
        # all_priorities=true, n=7 (все задачи). Сортировка по asc(priority), desc(created_at)
        response = client.get("/tasks/top/?all_priorities=true&n=7", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 7
        # Ожидаемый порядок: П0_Новая, П0_Старая, Задача_В(П1), Задача_Б(П2), Задача_А(П3), П5_Новая, П5_Старая
        expected_titles_all_prio = [
            self.task_p0_new.title, self.task_p0_old.title,  # Приоритет 0 (отсортировано по created_at desc)
            self.task_c.title,  # Приоритет 1
            self.task_b.title,  # Приоритет 2
            self.task_a.title,  # Приоритет 3
            self.task_p5_new.title, self.task_p5_old.title  # Приоритет 5 (отсортировано по created_at desc)
        ]
        assert [t["title"] for t in data] == expected_titles_all_prio

        # Тест с n < общего количества задач
        response_n3 = client.get("/tasks/top/?all_priorities=true&n=3", headers=auth_headers)
        assert response_n3.status_code == 200
        data_n3 = response_n3.json()
        assert len(data_n3) == 3
        assert [t["title"] for t in data_n3] == expected_titles_all_prio[:3]