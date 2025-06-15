import pytest
from httpx import AsyncClient
from backend import main


async def _auth_headers(client: AsyncClient, username="babbibo", password="babbibo"):
    # Регистрация
    await client.post("/register", json={"username": username, "password": password})
    # Авторизация
    token_resp = await client.post(
        "/token",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    token = token_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_update_task_success_and_cache_cleared(aclient: AsyncClient):
    # 1) Аутентифицируемся
    headers = await _auth_headers(aclient, "upduser", "upduser")

    # 2) Создаём задачу с полным payload
    create = await aclient.post(
        "/tasks",
        json={
            "title": "orig",
            "description": "desc",
            "status": "в ожидании",
            "priority": 1,
        },
        headers=headers,
    )
    assert create.status_code == 200
    task = create.json()
    task_id = task["id"]

    # 3) Запрашиваем список, чтобы заполнить кэш
    r1 = await aclient.get("/tasks", headers=headers)
    assert r1.status_code == 200
    assert main.cache_data["tasks"] is not None

    # 4) Обновляем ВСЕ поля, включая status
    payload = {
        "title": "updated",
        "description": "new desc",
        "status": "в работе",
        "priority": 5,
    }
    r_upd = await aclient.put(f"/tasks/{task_id}", json=payload, headers=headers)
    assert r_upd.status_code == 200
    updated = r_upd.json()

    # 5) Проверяем, что поля изменились
    assert updated["id"] == task_id
    assert updated["title"] == "updated"
    assert updated["description"] == "new desc"
    assert updated["status"] == "в работе"
    assert updated["priority"] == 5

    # 6) И кэш был очищен
    assert main.cache_data["tasks"] is None


@pytest.mark.asyncio
async def test_update_task_not_found_returns_404(aclient: AsyncClient):
    headers = await _auth_headers(aclient, "babababas", "babababas")
    payload = {"title": "updated", "description": "new desc", "priority": 5}

    # Пытаемся обновить несуществующую задачу
    r = await aclient.put(
        "/tasks/9999",
        json=payload,
        headers=headers,
    )
    assert r.status_code == 422
    assert r.json()["detail"][0]["msg"] == "Field required"
