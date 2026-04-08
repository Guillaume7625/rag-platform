from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.db.models.membership import Membership
from app.db.models.user import User


class AuthService:
    def authenticate(self, db: Session, email: str, password: str) -> tuple[User, Membership] | None:
        user = db.query(User).filter(User.email == email).first()
        if not user or not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        membership = db.query(Membership).filter(Membership.user_id == user.id).first()
        if not membership:
            return None
        return user, membership

    def issue_token(self, user: User, membership: Membership) -> str:
        return create_access_token(
            subject=str(user.id),
            extra={"tenant_id": str(membership.tenant_id), "role": membership.role},
        )


_auth: AuthService | None = None


def get_auth_service() -> AuthService:
    global _auth
    if _auth is None:
        _auth = AuthService()
    return _auth
