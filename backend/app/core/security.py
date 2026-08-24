from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from app.config import get_settings

settings = get_settings()

ALGORITHM = "HS256"
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"
_BCRYPT_ROUNDS = 12


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def create_access_token(subject: str, additional_claims: Optional[dict] = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    claims = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": TOKEN_TYPE_ACCESS,
    }
    if additional_claims:
        claims.update(additional_claims)
    return jwt.encode(claims, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    claims = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": TOKEN_TYPE_REFRESH,
    }
    return jwt.encode(claims, settings.secret_key, algorithm=ALGORITHM)


def verify_token(token: str, token_type: str) -> Optional[str]:
    """Verify token and return subject (user_id) or None if invalid."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        if payload.get("type") != token_type:
            return None
        subject: str = payload.get("sub")
        if subject is None:
            return None
        return subject
    except JWTError:
        return None
