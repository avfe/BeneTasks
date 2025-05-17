import pytest
from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt as pyjwt  # Псевдоним, чтобы избежать конфликта, если импортирован main.jwt
import time  # Для тестирования кэша

# Предполагается, что они импортированы из вашего основного файла приложения (например, main.py)
from main import (
    verify_password, get_password_hash,
    create_access_token, decode_token,
    SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES,
    clear_cache, cache_data, CACHE_TIMEOUT  # Для тестирования кэша
)

# Этот контекст должен совпадать с контекстом в вашем приложении
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def test_password_hashing_and_verification():
    password = "mypassword123"
    hashed_password = get_password_hash(password)
    assert isinstance(hashed_password, str)
    assert hashed_password != password
    assert verify_password(password, hashed_password)
    assert not verify_password("wrongpassword", hashed_password)


def test_create_access_token_default_expiry():
    data = {"sub": "test_user_sub"}
    token = create_access_token(data)
    assert isinstance(token, str)

    # Базовая проверка структуры JWT
    parts = token.split('.')
    assert len(parts) == 3

    # Декодируем для проверки содержимого и времени истечения
    payload = pyjwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "test_user_sub"
    expected_expiry_time = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # Допускаем небольшую дельту на время выполнения
    assert abs((datetime.fromtimestamp(payload["exp"]) - expected_expiry_time).total_seconds()) < 5


def test_create_access_token_custom_expiry():
    data = {"sub": "test_user_sub_custom"}
    custom_delta = timedelta(hours=1)
    token = create_access_token(data, expires_delta=custom_delta)
    payload = pyjwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "test_user_sub_custom"
    expected_expiry_time = datetime.utcnow() + custom_delta
    assert abs((datetime.fromtimestamp(payload["exp"]) - expected_expiry_time).total_seconds()) < 5


def test_decode_token_valid():
    username = "validuser"
    token = create_access_token(data={"sub": username})
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == username
    assert "exp" in payload


def test_decode_token_expired():
    username = "expireduser"
    # Создаем токен, который истек 10 секунд назад
    token = create_access_token(data={"sub": username}, expires_delta=timedelta(seconds=-10))
    # Ждем немного, чтобы убедиться, что он точно истек, если системные часы немного расходятся
    time.sleep(0.01)
    payload = decode_token(token)
    assert payload is None, "Токен должен считаться недействительным (истекшим)"


def test_decode_token_invalid_signature():
    username = "tampereduser"
    token_data = {"sub": username, "exp": datetime.utcnow() + timedelta(minutes=15)}
    # Кодируем с другим секретным ключом
    invalid_token = pyjwt.encode(token_data, "another_wrong_secret_key", algorithm=ALGORITHM)
    payload = decode_token(invalid_token)
    assert payload is None, "Токен с неверной подписью должен быть None"


def test_decode_token_malformed():
    malformed_token = "this.is.not.a.valid.jwt.token"
    payload = decode_token(malformed_token)
    assert payload is None, "Некорректный токен должен быть None"

    payload_no_sub = decode_token(create_access_token(data={"foo": "bar"}))
    # Сам decode_token не проверяет наличие 'sub', это делает get_current_user.
    # Здесь мы просто проверяем, декодируется ли он.
    assert payload_no_sub is not None
    assert "foo" in payload_no_sub


def test_cache_clear():
    # Заполняем кэш фиктивными данными
    cache_data["tasks"] = [{"id": 1, "title": "Фиктивная задача из кэша"}]
    cache_data["timestamp"] = time.time()

    assert cache_data["tasks"] is not None
    assert cache_data["timestamp"] != 0

    clear_cache()

    assert cache_data["tasks"] is None
    assert cache_data["timestamp"] == 0