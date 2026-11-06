# auth.py — Password security + JWT token ki logic
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

import models
from database import get_db
import os

# Token sign karne wali secret key. Production me isay .env file me rakho!
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-change-me")
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 din

# Bcrypt: password → secure hash converter
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# oauth2_scheme: request ke "Authorization: Bearer <token>" header se
# token nikalne wala helper (aur Swagger /docs me Authorize button bhi deta hai)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


def hash_password(password: str) -> str:
    """Naya password register karte waqt hash ban kare save karo."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Login ke waqt: daala hua password hash se match hota hai?"""
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int) -> str:
    """User ko apna digital pass (token) do — 24 ghante valid."""
    payload = {
        "sub": str(user_id),  # kis user ka token hai
        "exp": datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """Har protected route pe lagne wala check:
    token sahi hai? → user return karo. Nahi → 401 (login dobara karo)."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalid ya expire — dobara login karein",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise credentials_error

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_error
    return user
