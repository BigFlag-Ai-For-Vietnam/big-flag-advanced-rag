"""Đăng ký toàn bộ model để metadata biết trước khi create_all."""
from app.models.document import Document, DocumentStatus, GraphStatus
from app.models.page import Page
from app.models.chunk import Chunk

__all__ = ["Document", "DocumentStatus", "GraphStatus", "Page", "Chunk"]
