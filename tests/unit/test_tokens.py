import jwt
import pytest
from datetime import timedelta, datetime

import main

def test_create_access_token_custom_expiry():
    delta = timedelta(seconds=60)
    token = main.create_access_token({"sub": "alice"}, expires_delta=delta)
    payload = jwt.decode(token, main.SECRET_KEY, algorithms=[main.ALGORITHM])
    exp = datetime.fromtimestamp(payload["exp"])
    assert 50 <= (exp - datetime.utcnow()).total_seconds() <= 11000

def test_decode_token_invalid():
    broken = "abc.def.ghi"
    assert main.decode_token(broken) is None
