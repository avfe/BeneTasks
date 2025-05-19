async def _auth(aclient):
    await aclient.post("/register", json={"username": "tom", "password": "123456"})
    token = (
        await aclient.post(
            "/token",
            data={"username": "tom", "password": "123456"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_top_tasks_by_priority(aclient):
    headers = await _auth(aclient)

    # создаём 10 задач с разными приоритетами
    for pr in range(1, 6):
        for _ in range(4):
            await aclient.post(
                "/tasks",
                json={
                    "title": f"prio-{pr}",
                    "description": "...",
                    "priority": pr,
                },
                headers=headers,
            )

    # --- топ-3 priorité==5 ----------------------------------------
    r = await aclient.get("/tasks/top/?n=3&priority=5", headers=headers)
    assert r.status_code == 200
    top = r.json()
    assert len(top) == 3
    assert all(t["priority"] == 5 for t in top)

    # --- топ по всем приоритетам ----------------------------------
    r2 = await aclient.get("/tasks/top/?n=5&all_priorities=true", headers=headers)
    assert r2.status_code == 200
    body = r2.json()
    assert body == sorted(body, key=lambda t: t["priority"])
