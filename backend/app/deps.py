from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import User, UserSession
from app.security import hash_token

__all__ = ["get_db", "get_current_user", "require_admin", "require_document_deleter"]


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    unauthorized = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = request.cookies.get(get_settings().session_cookie_name)
    if not token:
        raise unauthorized

    row = db.execute(
        select(UserSession, User)
        .join(User, User.id == UserSession.user_id)
        .where(UserSession.token_hash == hash_token(token))
    ).first()
    if row is None:
        raise unauthorized

    session, user = row
    if _as_utc(session.expires_at) <= datetime.now(timezone.utc):
        db.delete(session)
        db.commit()
        raise unauthorized
    if not user.is_active:
        raise unauthorized
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return user


def require_document_deleter(user: User = Depends(get_current_user)) -> User:
    if user.username != get_settings().document_delete_username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to delete documents")
    return user
