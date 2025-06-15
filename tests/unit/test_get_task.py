import pytest
from httpx import AsyncClient


async def _auth_headers(client: AsyncClient, username="getter", password="pass123"):
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
async def test_get_task_success(aclient: AsyncClient):
    # 1) Аутентифицируемся
    headers = await _auth_headers(aclient, "getter", "pass123")

    # 2) Создаём задачу
    resp = await aclient.post(
        "/tasks",
        json={
            "title": "check-get",
            "description": "desc",
            "status": "в ожидании",
            "priority": 2,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    task = resp.json()
    task_id = task["id"]

    # 3) Получаем эту же задачу
    r = await aclient.get(f"/tasks/{task_id}", headers=headers)
    assert r.status_code == 200
    got = r.json()
    # проверяем, что поля совпадают с тем, что создали
    assert got["id"] == task_id
    assert got["title"] == "check-get"
    assert got["description"] == "desc"
    assert got["status"] == "в ожидании"
    assert got["priority"] == 2


@pytest.mark.asyncio
async def test_get_task_not_found(aclient: AsyncClient):
    headers = await _auth_headers(aclient, "getter2", "pass123")

    # Пытаемся получить несуществующую задачу
    r = await aclient.get("/tasks/999999", headers=headers)
    assert r.status_code == 404
    assert r.json()["detail"] == "Задача не найдена"
