import time
from httpx import AsyncClient
import pytest

import main


@pytest.mark.asyncio
async def test_in_memory_cache_behavior(aclient: AsyncClient):
    # регистрируемся -> получаем хедеры
    await aclient.post("/register", json={"username": "boobybo", "password": "boobybo"})
    token = (
        await aclient.post(
            "/token",
            data={"username": "boobybo", "password": "boobybo"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    ).json()
    hdrs = {"Authorization": f"Bearer {token}"}

    # 1-й запрос — кэш пустой
    first = await aclient.get("/tasks", headers=hdrs)
    assert first.status_code == 401
    assert main.cache_data["tasks"] is None

    # 2-й запрос через < CACHE_TIMEOUT — должен отдать из кэша
    before = time.time()
    second = await aclient.get("/tasks", headers=hdrs)
    assert second.elapsed.total_seconds() < 0.05  # очень быстро

    # инвалидируем кэш созданием задачи
    await aclient.post(
        "/tasks",
        json={"title": "t", "description": "d", "status": "в ожидании"},
        headers=hdrs,
    )
    assert main.cache_data["tasks"] is None


@pytest.mark.asyncio
async def test_wrong_sort_parameter(aclient: AsyncClient):
    await aclient.post("/register", json={"username": "eve", "password": "pass123"})
    token = (
        await aclient.post(
            "/token",
            data={"username": "eve", "password": "pass123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    ).json()["access_token"]
    hdrs = {"Authorization": f"Bearer {token}"}

    r = await aclient.get("/tasks?sort_by=unknown", headers=hdrs)
    assert r.status_code == 400
    assert r.json()["detail"] == "Неверный параметр сортировки"
