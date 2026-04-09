import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.models.user import User
from app.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


@dataclass
class CurrentUser:
    id: uuid.UUID
    email: str
    tenant_id: uuid.UUID
    role: str
    full_name: str | None = None

    @property
    def allowed_roles(self) -> list[str]:
        # Hierarchy: admin > member > guest.
        hierarchy = ["guest", "member", "admin"]
        idx = hierarchy.index(self.role) if self.role in hierarchy else 0
        return hierarchy[: idx + 1]


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> CurrentUser:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing token")
    try:
        payload = decode_access_token(token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token") from e

    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    role = payload.get("role", "member")
    if not user_id or not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid claims")

    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user inactive")

    return CurrentUser(
        id=user.id,
        email=user.email,
        tenant_id=uuid.UUID(tenant_id),
        role=role,
        full_name=user.full_name,
    )
