"""Seed a demo tenant, user and membership."""
from __future__ import annotations

from app.core.security import hash_password
from app.db.models.membership import Membership
from app.db.models.tenant import Tenant
from app.db.models.user import User
from app.db.session import SessionLocal


def run() -> None:
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.slug == "demo").first()
        if not tenant:
            tenant = Tenant(name="Demo", slug="demo")
            db.add(tenant)
            db.flush()

        user = db.query(User).filter(User.email == "demo@rag.local").first()
        if not user:
            user = User(
                email="demo@rag.local",
                password_hash=hash_password("demo1234"),
                full_name="Demo User",
                is_active=True,
            )
            db.add(user)
            db.flush()

        membership = (
            db.query(Membership)
            .filter(Membership.user_id == user.id, Membership.tenant_id == tenant.id)
            .first()
        )
        if not membership:
            db.add(Membership(user_id=user.id, tenant_id=tenant.id, role="admin"))

        db.commit()
        print("seeded:", tenant.slug, user.email)
    finally:
        db.close()


if __name__ == "__main__":
    run()
