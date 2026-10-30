from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db import build_engine, get_db
from app.deps import require_admin
from app.main import create_app
from app.models import User
from app.security import hash_password

TEST_PASSWORD = "correct-horse-battery"
BACKEND_DIR = Path(__file__).resolve().parent.parent


def run_migrations(database_url: str) -> None:
    config = Config()
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


@pytest.fixture(autouse=True)
def storage_path(tmp_path, monkeypatch) -> Iterator[Path]:
    path = tmp_path / "storage"
    path.mkdir()
    monkeypatch.setenv("STORAGE_PATH", str(path))
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    get_settings.cache_clear()
    yield path
    get_settings.cache_clear()


@pytest.fixture
def session_factory(tmp_path) -> Iterator[sessionmaker[Session]]:
    database_url = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    run_migrations(database_url)
    engine = build_engine(database_url)
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


@pytest.fixture
def login_as(client, create_user) -> Callable[..., User]:
    def _login(username: str = "alice", role: str = "admin") -> User:
        user = create_user(username=username, role=role)
        client.cookies.clear()
        response = client.post("/api/auth/login", json={"username": username, "password": TEST_PASSWORD})
        assert response.status_code == 200
        return user

    return _login
