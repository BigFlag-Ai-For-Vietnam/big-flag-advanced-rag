"""Khởi tạo SQLAlchemy engine / session / Base cho SQLite."""
import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

# Với SQLite cần check_same_thread=False để dùng chung engine giữa các thread (BackgroundTasks).
connect_args = {"check_same_thread": False} if settings.db_url.startswith("sqlite") else {}

# Đảm bảo thư mục chứa file .db tồn tại.
if settings.db_url.startswith("sqlite:///"):
    db_path = settings.db_url.replace("sqlite:///", "", 1)
    parent = os.path.dirname(db_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

engine = create_engine(settings.db_url, connect_args=connect_args, future=True)


@event.listens_for(engine, "connect")
def _enable_sqlite_fk(dbapi_conn, _record):
    """Bật ràng buộc khóa ngoại (mặc định SQLite tắt) để cascade delete hoạt động."""
    if settings.db_url.startswith("sqlite"):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: mở session, đảm bảo đóng sau request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Tạo bảng nếu chưa có (v1 dùng create_all thay cho Alembic)."""
    # import models để đăng ký metadata trước khi create_all
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
