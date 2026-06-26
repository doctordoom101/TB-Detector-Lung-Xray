import jwt
import datetime
import hashlib
import bcrypt
from app.core.config import settings

def _prepare_password(password: str) -> bytes:
    """
    Mengatasi bug passlib + modern bcrypt pada Python 3.10+.
    Melakukan pre-hash menggunakan SHA-256 dan diubah ke bentuk hex (64 karakter / 64 bytes).
    Ini memastikan panjang password selalu di bawah batas maksimum bcrypt (72 bytes) 
    dan mencegah ValueError dari library bcrypt versi terbaru.
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest().encode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Memverifikasi kesamaan password asli dengan hash"""
    try:
        secret = _prepare_password(plain_password)
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(secret, hashed_bytes)
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """Mengubah password menjadi hash bcrypt aman"""
    secret = _prepare_password(password)
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(secret, salt)
    return hashed.decode("utf-8")

def create_access_token(data: dict):
    """Membuat JWT Access Token"""
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    """Membaca dan memverifikasi JWT Token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None
