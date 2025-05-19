import pytest


async def test_register_and_login(aclient):
    # регистрация
    resp = await aclient.post(
        "/register",
        json={"username": "bob", "password": "123456"},
    )
    assert resp.status_code == 200

    # авторизация и получение JWT
    token_resp = await aclient.post(
        "/token",
        data={"username": "bob", "password": "123456"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert token_resp.status_code == 200
    token_data = token_resp.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"


@pytest.mark.parametrize(
    "payload",
    [
        {"username": "a", "password": "abc"},  # too short password?
        {"username": "", "password": "123456"},
        {"username": "bob"},
    ],
)
async def test_register_validation_errors(aclient, payload):
    resp = await aclient.post("/register", json=payload)
    assert resp.status_code == 422
