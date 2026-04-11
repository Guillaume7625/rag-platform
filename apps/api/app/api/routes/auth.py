import hashlib
import hmac

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user
from app.core.config import settings
from app.core.rate_limit import login_limiter, register_limiter
from app.core.security import hash_password
from app.db.models.membership import Membership
from app.db.models.tenant import Tenant
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut, UserUpdate
from app.services.auth_service import get_auth_service
from app.services.email_service import notify_new_registration

router = APIRouter(prefix="/auth", tags=["auth"])


def _approval_token(user_id: str) -> str:
    """Generate a simple HMAC token for email approval links."""
    return hmac.new(
        settings.jwt_secret.encode(), user_id.encode(), hashlib.sha256
    ).hexdigest()[:32]


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    request: Request, payload: RegisterRequest, db: Session = Depends(get_db),
) -> dict:
    register_limiter.check(request)
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
        is_active=False,  # Requires admin approval
    )
    db.add(user)
    db.flush()
    tenant = Tenant(name=f"{payload.email}'s workspace", slug=str(user.id)[:8])
    db.add(tenant)
    db.flush()
    membership = Membership(user_id=user.id, tenant_id=tenant.id, role="admin")
    db.add(membership)
    db.commit()
    notify_new_registration(
        email=payload.email,
        full_name=payload.full_name,
        user_id=str(user.id),
        approval_token=_approval_token(str(user.id)),
    )
    return {
        "status": "pending",
        "message": "Votre demande d'inscription a bien ete envoyee. "
        "Vous recevrez un acces une fois votre compte valide par l'administrateur.",
    }


@router.get("/approve/{user_id}/{token}", response_class=HTMLResponse)
def approve_user(user_id: str, token: str, db: Session = Depends(get_db)) -> str:
    """Approve a user registration via link in email."""
    expected = _approval_token(user_id)
    if not hmac.compare_digest(token, expected):
        return HTMLResponse(
            "<h2>Lien invalide</h2><p>Ce lien d'approbation n'est pas valide.</p>",
            status_code=403,
        )
    import uuid as _uuid

    user = db.query(User).filter(User.id == _uuid.UUID(user_id)).first()
    if not user:
        return HTMLResponse("<h2>Utilisateur introuvable</h2>", status_code=404)
    if user.is_active:
        return HTMLResponse(
            f"<h2>Deja approuve</h2><p>{user.email} est deja actif.</p>"
        )

    user.is_active = True
    db.commit()
    return HTMLResponse(f"""
    <html>
    <head><meta charset="utf-8"><style>
      body {{ font-family: Arial, sans-serif; max-width: 500px; margin: 80px auto; text-align: center; }}
      h2 {{ color: #16a34a; }}
      .email {{ font-weight: bold; color: #1c1917; }}
    </style></head>
    <body>
      <h2>Compte approuve</h2>
      <p><span class="email">{user.email}</span> peut maintenant se connecter.</p>
      <p><a href="https://rag.marinenationale.cloud/login">Aller sur la plateforme</a></p>
    </body>
    </html>
    """)


@router.post("/login", response_model=TokenResponse)
def login(
    request: Request, payload: LoginRequest, db: Session = Depends(get_db),
) -> TokenResponse:
    login_limiter.check(request)
    svc = get_auth_service()
    result = svc.authenticate(db, payload.email, payload.password)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
        )
    user, membership = result
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Votre compte est en attente de validation par l'administrateur.",
        )
    token = svc.issue_token(user, membership)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
def me(
    current: CurrentUser = Depends(get_current_user),
) -> UserOut:
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
