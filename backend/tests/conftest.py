from collections.abc import Callable, Iterator

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.db import Base, build_engine, get_db
from app.deps import require_admin
from app.main import create_app
from app.models import User
from app.security import hash_password

TEST_PASSWORD = "correct-horse-battery"


@pytest.fixture
def session_factory(tmp_path) -> Iterator[sessionmaker[Session]]:
    engine = build_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    engine.dispose()


@pytest.fixture
def client(session_factory) -> Iterator[TestClient]:
    app = create_app()

    @app.get("/api/test/admin-only")
    def admin_only(user: User = Depends(require_admin)) -> dict[str, str]:
        return {"username": user.username}

    def override_get_db() -> Iterator[Session]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def create_user(session_factory) -> Callable[..., User]:
    def _create(username: str = "alice", role: str = "admin", is_active: bool = True) -> User:
        with session_factory() as db:
            user = User(
                username=username,
                full_name=f"{username.title()} Tester",
                password_hash=hash_password(TEST_PASSWORD),
                role=role,
                is_active=is_active,
            )
            db.add(user)
            db.commit()
            return user

    return _create
