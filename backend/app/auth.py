"""
Mock authentication module.

Users and their account/role mappings are hardcoded here for assessment purposes.
In production this would connect to a real auth provider.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from .config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


# ---------------------------------------------------------------------------
# Mock user store
# ---------------------------------------------------------------------------
MOCK_USERS = {
    "northstar": {
        "username": "northstar",
        "password": "pilot123",
        "full_name": "Alex Chen (Northstar Logistics)",
        "role": "customer",
        "account_id": "ACCT-001",
        "account_name": "Northstar Logistics",
        "customer_scope": "northstar",
    },
    "lumenworks": {
        "username": "lumenworks",
        "password": "pilot123",
        "full_name": "Jordan Kim (LumenWorks)",
        "role": "customer",
        "account_id": "ACCT-002",
        "account_name": "LumenWorks",
        "customer_scope": "lumenworks",
    },
    "support": {
        "username": "support",
        "password": "pilot123",
        "full_name": "Sam Rivera (Support Agent)",
        "role": "internal",
        "account_id": None,
        "account_name": None,
        "customer_scope": None,
    },
    "ops": {
        "username": "ops",
        "password": "pilot123",
        "full_name": "Morgan Lee (Ops Manager)",
        "role": "ops_manager",
        "account_id": None,
        "account_name": None,
        "customer_scope": None,
    },
}


class UserContext(BaseModel):
    username: str
    full_name: str
    role: str  # "customer" | "internal" | "ops_manager"
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    customer_scope: Optional[str] = None

    @property
    def is_internal(self) -> bool:
        return self.role in ("internal", "ops_manager")

    @property
    def is_customer(self) -> bool:
        return self.role == "customer"


def authenticate_user(username: str, password: str) -> Optional[dict]:
    user = MOCK_USERS.get(username)
    if not user or user["password"] != password:
        return None
    return user


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> UserContext:
    import sys
    print(f"[AUTH DEBUG] incoming token present: {bool(token)}, value_start: {token[:20] if token else 'NONE'}", flush=True, file=sys.stderr)
    if token:
        try:
            payload = jwt.decode(
                token, settings.secret_key, algorithms=[settings.algorithm]
            )
            username: str = payload.get("sub")
            if username and username in MOCK_USERS:
                user_data = MOCK_USERS[username]
                print(f"[AUTH DEBUG] resolved user from token: username={username} account_id={user_data.get('account_id')}", flush=True, file=sys.stderr)
                return UserContext(
                    username=user_data["username"],
                    full_name=user_data["full_name"],
                    role=user_data["role"],
                    account_id=user_data.get("account_id"),
                    account_name=user_data.get("account_name"),
                    customer_scope=user_data.get("customer_scope"),
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Default fallback to northstar persona only if no token header was sent at all
    import sys
    print(f"[AUTH DEBUG] NO TOKEN - falling back to northstar default", flush=True, file=sys.stderr)
    user_data = MOCK_USERS["northstar"]
    return UserContext(
        username=user_data["username"],
        full_name=user_data["full_name"],
        role=user_data["role"],
        account_id=user_data.get("account_id"),
        account_name=user_data.get("account_name"),
        customer_scope=user_data.get("customer_scope"),
    )


def require_internal(user: UserContext = Depends(get_current_user)) -> UserContext:
    if not user.is_internal:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is restricted to internal ParcelPilot staff.",
        )
    return user
