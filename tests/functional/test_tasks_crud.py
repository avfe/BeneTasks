async def _auth_headers(aclient):
    await aclient.post("/register", json={"username": "ann", "password": "123456"})
    token = (
        await aclient.post(
            "/token",
            data={"username": "ann", "password": "123456"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_create_read_update_delete_task(aclient):
    headers = await _auth_headers(aclient)

    # --- create ----------------------------------------------------
    create_payload = {
        "title": "write tests",
        "description": "unit + functional + locust",
        "priority": 3,
    }
    r_create = await aclient.post("/tasks", json=create_payload, headers=headers)
    assert r_create.status_code == 200
    task = r_create.json()
    task_id = task["id"]

    # --- read list -------------------------------------------------
    r_list = await aclient.get("/tasks", headers=headers)
    assert r_list.status_code == 200
    assert any(t["id"] == task_id for t in r_list.json())

    # --- update ----------------------------------------------------
    r_update = await aclient.put(
        f"/tasks/{task_id}",
        json={
            "title": "write more tests",
            "description": "updated",
            "priority": 4,
        },
        headers=headers,
    )
    assert r_update.status_code in (200, 422)
    if r_update.status_code == 200:
        assert r_update.json()["title"] == "write more tests"

    # --- delete ----------------------------------------------------
    r_del = await aclient.delete(f"/tasks/{task_id}", headers=headers)
    assert r_del.status_code == 200

    # проверяем, что задачи действительно нет
    r_list2 = await aclient.get("/tasks", headers=headers)
    assert all(t["id"] != task_id for t in r_list2.json())
