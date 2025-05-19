from passlib.context import CryptContext

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def test_password_hashing_roundtrip():
    raw = "s3cr3tPa55!"
    hashed = pwd_ctx.hash(raw)
    assert pwd_ctx.verify(raw, hashed), "Пароль после хеширования не верифицируется"

    # хеши разные при каждом вызове
    assert hashed != pwd_ctx.hash(raw)
