import asyncio
from faker import Faker

fake = Faker()


async def _headers(aclient):
    await aclient.post("/register", json={"username": "kate", "password": "123456"})
    token = (
        await aclient.post(
            "/token",
            data={"username": "kate", "password": "123456"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _bulk_create(aclient, headers, n=30):
    tasks = [
        {"title": fake.word(), "description": fake.text(), "priority": i % 5 + 1}
        for i in range(n)
    ]
    await asyncio.gather(
        *[aclient.post("/tasks", json=task, headers=headers) for task in tasks]
    )
    return tasks


async def test_search_and_sort(aclient):
    headers = await _headers(aclient)
    tasks = await _bulk_create(aclient, headers)

    # фильтрация по подстроке
    substr = tasks[0]["title"][:3]
    r_search = await aclient.get(f"/tasks?search={substr}", headers=headers)
    assert r_search.status_code == 200

    assert all(
        substr.lower() in (t["title"] + t["description"]).lower()
        for t in r_search.json()
    )

    # сортировка по дате desc
    r_sort = await aclient.get("/tasks?sort_by=created_at&order=desc", headers=headers)
    body = r_sort.json()
    assert body == sorted(body, key=lambda x: x["created_at"], reverse=True)
