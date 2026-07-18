"""Khởi tạo SQLAlchemy engine / session / Base cho SQLite."""
import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings

# Với SQLite cần check_same_thread=False để dùng chung engine giữa các thread (BackgroundTasks).
connect_args = {"check_same_thread": False} if settings.db_url.startswith("sqlite") else {}

# Đảm bảo thư mục chứa file .db tồn tại.
if settings.db_url.startswith("sqlite:///"):
    db_path = settings.db_url.replace("sqlite:///", "", 1)
    parent = os.path.dirname(db_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

# NullPool cho SQLite: nhiều thread mở SessionLocal() riêng cùng lúc (BackgroundTasks +
# kg-build loop) — QueuePool mặc định (size=5, overflow=10) hết chỗ dưới tải thật, timeout
# 30s rồi 500 (đã bắt gặp lúc test thật: upload document thứ 9 lỗi vì hết pool). SQLite mở
# connection rẻ nên bỏ giới hạn pool thay vì đoán số cố định.
engine_kwargs = {"poolclass": NullPool} if settings.db_url.startswith("sqlite") else {}
engine = create_engine(settings.db_url, connect_args=connect_args, future=True, **engine_kwargs)


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
    _auto_migrate_sqlite()


def _auto_migrate_sqlite() -> None:
    """Migration nhẹ cho SQLite: thêm cột còn thiếu vào bảng documents.

    create_all KHÔNG ALTER bảng đã tồn tại, nên DB cũ (trước khi có catalog) sẽ thiếu
    category/focus_entities/catalog. Thêm cột ở đây để giữ nguyên dữ liệu + blob cũ,
    cho phép reprocess tài liệu cũ mà không cần xoá volume. Idempotent.
    """
    if not settings.db_url.startswith("sqlite"):
        return
    # SQLAlchemy JSON map sang TEXT trong SQLite.
    new_columns = {
        "category": "VARCHAR(64)",
        "focus_entities": "JSON",
        "catalog": "JSON",
        "graph_status": "VARCHAR(20)",
        "graph_error_message": "TEXT",
    }
    with engine.begin() as conn:
        existing = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(documents)")}
        for col, ddl in new_columns.items():
            if col not in existing:
                conn.exec_driver_sql(f"ALTER TABLE documents ADD COLUMN {col} {ddl}")
