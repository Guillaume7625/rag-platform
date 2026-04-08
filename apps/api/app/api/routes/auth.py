from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user
from app.db.session import get_db
from app.schemas.auth import LoginRequest, TokenResponse, UserOut
from app.services.auth_service import get_auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    svc = get_auth_service()
    result = svc.authenticate(db, payload.email, payload.password)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
        )
    user, membership = result
    token = svc.issue_token(user, membership)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
def me(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserOut:
    return UserOut(
        id=current.id,
        email=current.email,
        full_name=None,
        tenant_id=current.tenant_id,
        role=current.role,
    )
