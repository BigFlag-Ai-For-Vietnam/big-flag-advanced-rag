"""Test storage_service backend "local" (không gọi API ngoài, không cần boto3).

Ghi/đọc/xoá blob dưới data_dir tạm; ép storage_backend="local" qua settings.
"""
import pytest

from app.config import settings
from app.services import storage_service


@pytest.fixture
def local_store(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", str(tmp_path))
    monkeypatch.setattr(settings, "storage_backend", "local")
    return tmp_path


def test_put_returns_key_and_roundtrips(local_store):
    key = storage_service.put_bytes("uploads/doc1.pdf", b"pdf-bytes")
    assert key == "uploads/doc1.pdf"
    assert storage_service.get_bytes("uploads/doc1.pdf") == b"pdf-bytes"
    # file thực nằm dưới data_dir/key
    assert (local_store / "uploads" / "doc1.pdf").read_bytes() == b"pdf-bytes"


def test_delete_prefix_removes_single_file(local_store):
    storage_service.put_bytes("uploads/doc1.pdf", b"x")
    storage_service.delete_prefix("uploads/doc1.pdf")
    assert not (local_store / "uploads" / "doc1.pdf").exists()


def test_delete_prefix_removes_directory_tree(local_store):
    storage_service.put_bytes("images/doc1/page_0001.png", b"a")
    storage_service.put_bytes("images/doc1/page_0002.png", b"b")
    storage_service.delete_prefix("images/doc1/")
    assert not (local_store / "images" / "doc1").exists()


def test_delete_prefix_missing_is_noop(local_store):
    # không raise khi key/thư mục không tồn tại
    storage_service.delete_prefix("uploads/nope.pdf")
    storage_service.delete_prefix("images/nope/")
