import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_task_not_found(aclient: AsyncClient):
    # создаём юзера только ради токена
    await aclient.post("/register", json={"username": "tmp", "password": "pass123"})
    token = (
        await aclient.post(
            "/token",
            data={"username": "tmp", "password": "pass123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    ).json()["access_token"]
    hdrs = {"Authorization": f"Bearer {token}"}

    r = await aclient.get("/tasks/999", headers=hdrs)  # ID, которого нет
    assert r.status_code == 404
    assert r.json()["detail"] == "Задача не найдена"
