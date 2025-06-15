import pytest
from httpx import AsyncClient


async def _auth_headers(ac: AsyncClient, name="bobbys"):
    await ac.post("/register", json={"username": name, "password": "bobbys"})
    token = (
        await ac.post(
            "/token",
            data={"username": name, "password": "bobbys"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_top_tasks_all_priorities_branch(aclient: AsyncClient):
    hd = await _auth_headers(aclient, "alice")

    # 1..3 задачи с разными приоритетами
    for pr in (1, 2, 3):
        await aclient.post(
            "/tasks",
            json={"title": f"t{pr}", "description": "x", "priority": pr},
            headers=hd,
        )

    r = await aclient.get("/tasks/top/?n=5&all_priorities=true", headers=hd)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 3
    # упорядочены по возрастанию priority
    assert [t["priority"] for t in data] == sorted(t["priority"] for t in data)


@pytest.mark.asyncio
async def test_top_tasks_default_branch(aclient: AsyncClient):
    hd = await _auth_headers(aclient, "charlie")

    # делаем больше «высоких» приоритетов
    for _ in range(3):
        await aclient.post(
            "/tasks",
            json={"title": "hi", "description": "x", "priority": 9},
            headers=hd,
        )
    # + пара низких
    for _ in range(2):
        await aclient.post(
            "/tasks",
            json={"title": "lo", "description": "x", "priority": 1},
            headers=hd,
        )

    r = await aclient.get("/tasks/top/?n=2", headers=hd)
    assert r.status_code == 200
    best = r.json()
    assert all(t["priority"] == 9 for t in best)  # взяты самые «тяжёлые»
