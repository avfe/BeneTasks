import pytest
from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


def test_get_current_user_bad_token(monkeypatch):
    # Подменяем зависимость, чтобы вызвать энд-поинт напрямую
    def fake_dep():
        return "invalid.token"
    main.app.dependency_overrides[main.oauth2_scheme] = fake_dep

    resp = client.get("/tasks")  # любой защищённый роут подойдёт
    assert resp.status_code == 401
    assert resp.json()["detail"] in {"Неверный токен", "Пользователь не найден"}

    main.app.dependency_overrides.clear()
