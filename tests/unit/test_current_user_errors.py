import pytest
from fastapi.testclient import TestClient
import main


client = TestClient(main.app)


def _override_token(value: str):
    """Возвращаем фейковый токен вместо oauth2_scheme."""
    main.app.dependency_overrides[main.oauth2_scheme] = lambda: value


@pytest.mark.parametrize(
    "token, expected_detail",
    [
        ("bad.token", "Неверный токен"),          # decode_token → None
        (main.create_access_token({}), "Неверный токен"),          # sub отсутствует
        (main.create_access_token({"sub": "ghost"}), "Пользователь не найден"),  # нет такого
    ],
)
def test_get_current_user_error_branches(token, expected_detail):
    _override_token(token)
    resp = client.get("/tasks")       # любой защищённый эндпоинт
    assert resp.status_code == 401
    assert resp.json()["detail"] == expected_detail
    main.app.dependency_overrides.clear()
