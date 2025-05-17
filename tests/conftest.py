import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient
from datetime import datetime  # Для create_task_for_user

# Важно: Импортируем main.py как модуль, чтобы можно было патчить его глобальные переменные
import main as main_module
from main import app, Base, get_db, User, get_password_hash, Task  # Task для прямого создания в тестах

# Используем SQLite в памяти для тестирования
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"  # :memory: для SQLite в памяти


@pytest.fixture(scope="session")
def test_engine_instance():
    """
    Создает единственный экземпляр SQLAlchemy engine для всей тестовой сессии.
    Использует базу данных SQLite в памяти.
    """
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
    yield engine


@pytest.fixture(scope="function")
def db_setup_and_teardown(test_engine_instance, monkeypatch):
    """
    Фикстура для настройки базы данных для каждой тестовой функции.
    - Патчит main_module.engine и main_module.SessionLocal для использования тестовой БД.
      Это критично, чтобы app.on_event("startup") использовал тестовую БД.
    - Создает все таблицы.
    - Переопределяет зависимость get_db.
    - Удаляет все таблицы после теста.
    - Восстанавливает оригинальные атрибуты main_module и переопределения зависимостей.
    """
    original_engine = main_module.engine
    original_session_local = main_module.SessionLocal
    original_get_db_override = app.dependency_overrides.get(get_db)

    # Патчим engine и SessionLocal в модуле main
    monkeypatch.setattr(main_module, "engine", test_engine_instance)

    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine_instance)
    monkeypatch.setattr(main_module, "SessionLocal", TestSessionLocal)

    # Определяем переопределение для get_db для этой тестовой сессии
    def override_get_db_for_test():
        try:
            db = TestSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db_for_test

    # Создаем таблицы. Событие app.on_event("startup") также вызовет это,
    # и создаст пользователя admin в тестовой БД.
    Base.metadata.create_all(bind=test_engine_instance)

    yield TestSessionLocal  # Может использоваться другими фикстурами/тестами для получения sessionmaker

    # Завершение: Удаляем таблицы
    Base.metadata.drop_all(bind=test_engine_instance)

    # Восстанавливаем оригинальные атрибуты модуля main и переопределения зависимостей
    monkeypatch.setattr(main_module, "engine", original_engine)
    monkeypatch.setattr(main_module, "SessionLocal", original_session_local)
    if original_get_db_override:
        app.dependency_overrides[get_db] = original_get_db_override
    else:
        app.dependency_overrides.pop(get_db, None)
    main_module.clear_cache()  # Очищаем кэш после каждого теста


@pytest.fixture(scope="function")
def client(db_setup_and_teardown):
    """
    Предоставляет экземпляр TestClient для выполнения API-запросов.
    Зависит от db_setup_and_teardown, чтобы гарантировать, что БД готова и пропатчена.
    Инициализация TestClient вызовет события запуска приложения.
    """
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function")
def db_session(db_setup_and_teardown) -> Session:
    """
    Предоставляет прямую сессию SQLAlchemy для манипуляций с базой данных в тестах.
    """
    TestSessionLocal = db_setup_and_teardown  # Это sessionmaker, возвращаемый db_setup_and_teardown
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def test_user_data_factory():
    """Фабрика для создания уникальных данных пользователя во избежание конфликтов."""
    counter = 0

    def _factory():
        nonlocal counter
        counter += 1
        return {"username": f"testuser{counter}", "password": f"testpassword{counter}"}

    return _factory


@pytest.fixture(scope="function")
def test_user_data(test_user_data_factory):
    return test_user_data_factory()


@pytest.fixture(scope="function")
def created_test_user(db_session: Session, test_user_data: dict) -> User:
    """
    Создает пользователя напрямую в базе данных и возвращает объект User.
    """
    user = User(
        username=test_user_data["username"],
        hashed_password=get_password_hash(test_user_data["password"])
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_token_for_user(client: TestClient, test_user_data: dict, created_test_user: User) -> str:
    """
    Выполняет вход для created_test_user и возвращает токен доступа.
    Гарантирует, что фикстура created_test_user выполнится первой, чтобы пользователь существовал.
    """
    login_data = {
        "username": test_user_data["username"],
        "password": test_user_data["password"]
    }
    response = client.post("/token", data=login_data)
    assert response.status_code == 200, \
        f"Вход не удался для пользователя {test_user_data['username']}: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="function")
def auth_headers(auth_token_for_user: str) -> dict:
    """
    Возвращает заголовки аутентификации с токеном пользователя.
    """
    return {"Authorization": f"Bearer {auth_token_for_user}"}


@pytest.fixture(scope="function")
def admin_auth_token(client: TestClient) -> str:
    """
    Выполняет вход для пользователя admin (созданного событием запуска приложения) и возвращает токен доступа.
    Фикстура `client` гарантирует, что события запуска были выполнены.
    """
    login_data = {"username": "admin", "password": "admin"}
    response = client.post("/token", data=login_data)
    assert response.status_code == 200, f"Вход администратора не удался: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="function")
def admin_auth_headers(admin_auth_token: str) -> dict:
    """
    Возвращает заголовки аутентификации с токеном администратора.
    """
    return {"Authorization": f"Bearer {admin_auth_token}"}


@pytest.fixture(scope="function")
def create_task_for_user(db_session: Session, created_test_user: User):
    """Фабрика для создания задач для текущего test_user."""

    def _creator(title: str, description: str, status: str, priority: int, created_at: datetime = None) -> Task:
        task_data = {
            "title": title,
            "description": description,
            "status": status,
            "priority": priority,
            "owner_id": created_test_user.id
        }
        if created_at:
            task_data["created_at"] = created_at

        task = Task(**task_data)
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        return task

    return _creator