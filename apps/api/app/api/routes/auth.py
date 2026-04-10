from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user
from app.core.rate_limit import login_limiter
from app.core.security import hash_password
from app.db.models.membership import Membership
from app.db.models.tenant import Tenant
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut, UserUpdate
from app.services.auth_service import get_auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="email already registered",
        )
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    db.flush()
    tenant = Tenant(name=f"{payload.email}'s workspace", slug=str(user.id)[:8])
    db.add(tenant)
    db.flush()
    membership = Membership(user_id=user.id, tenant_id=tenant.id, role="admin")
    db.add(membership)
    db.commit()
    svc = get_auth_service()
    token = svc.issue_token(user, membership)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    login_limiter.check(request)
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
) -> UserOut:
    # full_name is populated on CurrentUser by get_current_user so we avoid a
    # second DB round-trip on this hot path.
    return UserOut(
        id=current.id,
        email=current.email,
        full_name=current.full_name,
        tenant_id=current.tenant_id,
        role=current.role,
    )


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UserUpdate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserOut:
    user = db.query(User).filter(User.id == current.id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="user not found",
        )
    user.full_name = payload.full_name
    db.commit()
    db.refresh(user)
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        tenant_id=current.tenant_id,
        role=current.role,
    )
