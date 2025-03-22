import jwt
from datetime import datetime, timedelta

SECRET_KEY = "e0c17ab5-06cd-4c23-acf0-9024ded21874"
ALGORITHM = "HS256"


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=30)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(days=30)  # Default to 30 days

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def refresh_access_token(refresh_token: str):
    try:
        user_data = decode(refresh_token)
        new_access_token = create_access_token(data=user_data)
        return new_access_token
    except jwt.ExpiredSignatureError:
        raise Exception("Refresh token has expired.")
    except jwt.InvalidTokenError:
        raise Exception("Invalid refresh token.")


def decode(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # payload
    except jwt.InvalidTokenError:
        raise Exception("Invalid token.")
