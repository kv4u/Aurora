"""JWT authentication for AURORA dashboard — single-user system."""

import logging
import sys
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

logger = logging.getLogger("aurora.auth")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


# ─── User Model ───

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)


# ─── Schemas ───

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


# ─── Token Utilities ───

def create_access_token(data: dict, secret: str, expires_minutes: int = 30) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret, algorithm="HS256")


def verify_token(token: str, secret: str) -> str | None:
    """Verify JWT and return username, or None if invalid."""
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except JWTError:
        return None


# ─── Password Utilities ───

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ─── Dependency: Get Current User ───

async def get_current_user(token: str | None = Depends(oauth2_scheme)):
    """FastAPI dependency — extracts user from JWT. Returns None if no token."""
    if token is None:
        return None

    from app.config import get_settings
    settings = get_settings()
    username = verify_token(token, settings.jwt_secret.get_secret_value())
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return username


async def require_auth(user: str | None = Depends(get_current_user)):
    """FastAPI dependency — requires authentication."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# ─── CLI: Create User ───

def create_user_cli():
    """CLI command to create the admin user.

    Usage: python -m app.security.auth create-user
    """
    import asyncio
    import getpass

    async def _create():
        from app.database import _get_session_maker

        username = input("Username: ").strip()
        if not username:
            print("Username cannot be empty.")
            return

        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm password: ")

        if password != confirm:
            print("Passwords don't match.")
            return
        if len(password) < 8:
            print("Password must be at least 8 characters.")
            return

        session_maker = _get_session_maker()
        async with session_maker() as session:
            # Check if user exists
            result = await session.execute(
                select(User).where(User.username == username)
            )
            if result.scalar_one_or_none():
                print(f"User '{username}' already exists.")
                return

            user = User(
                username=username,
                hashed_password=hash_password(password),
            )
            session.add(user)
            await session.commit()
            print(f"User '{username}' created successfully.")

    asyncio.run(_create())


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "create-user":
        create_user_cli()
    else:
        print("Usage: python -m app.security.auth create-user")
