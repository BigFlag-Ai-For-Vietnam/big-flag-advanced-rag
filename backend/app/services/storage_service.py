"""Lớp lưu trữ blob (PDF gốc + ảnh page) — một choke point duy nhất.

Giống `llm_client.py` gom mọi lời gọi FPT, module này gom mọi thao tác đọc/ghi/xoá
file nhị phân. Call site (router, pipeline, parsing) KHÔNG được gọi thẳng `boto3`
hay `open()` — luôn đi qua đây, để đổi backend chỉ sửa một chỗ.

Blob được định danh bằng **key** trung lập backend, vd:
    uploads/{document_id}.pdf
    images/{document_id}/page_0001.png

Hai backend chọn qua `settings.storage_backend`:
- "local" (mặc định): key ánh xạ tới `{data_dir}/{key}` trên đĩa — đúng bố cục cũ,
  nên hành vi giữ nguyên khi chưa bật S3.
- "s3": ghi vào bucket S3 (RustFS / bất kỳ endpoint S3-compatible) qua boto3.

`boto3` chỉ import bên trong nhánh s3 -> chế độ local và test offline không cần lib này.
"""
from __future__ import annotations

import logging
import os

from app.config import settings

logger = logging.getLogger("storage_service")


# --- Local backend ------------------------------------------------------------

def _local_path(key: str) -> str:
    """Ánh xạ key -> đường dẫn tuyệt đối dưới data_dir."""
    return os.path.join(settings.data_dir, key)


def _local_put(key: str, data: bytes) -> str:
    path = _local_path(key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)
    return key


def _local_get(key: str) -> bytes:
    with open(_local_path(key), "rb") as fh:
        return fh.read()


def _local_delete_prefix(prefix: str) -> None:
    """Xoá mọi file dưới prefix (best-effort). Prefix có thể là 1 file hoặc 1 thư mục."""
    base = _local_path(prefix)
    if os.path.isfile(base):
        try:
            os.remove(base)
        except OSError:
            pass
        return
    # Thư mục: xoá đệ quy nội dung rồi bỏ thư mục rỗng.
    if os.path.isdir(base):
        for root, _dirs, files in os.walk(base, topdown=False):
            for name in files:
                try:
                    os.remove(os.path.join(root, name))
                except OSError:
                    pass
            try:
                os.rmdir(root)
            except OSError:
                pass


# --- S3 backend (RustFS / S3-compatible) --------------------------------------

_s3_client = None


def _s3():  # -> boto3 S3 client (không annotate để tránh phụ thuộc type boto3)
    """Khởi tạo lazy boto3 client + đảm bảo bucket tồn tại (chỉ khi backend=s3)."""
    global _s3_client
    if _s3_client is not None:
        return _s3_client

    import boto3  # import cục bộ: chế độ local/test không cần boto3
    from botocore.exceptions import ClientError

    client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
    )
    # Tạo bucket nếu chưa có (idempotent) — thay cho service createbuckets của infra.
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
    except ClientError:
        try:
            client.create_bucket(Bucket=settings.s3_bucket)
            logger.info("Đã tạo bucket S3 '%s'", settings.s3_bucket)
        except ClientError as exc:
            logger.warning("Không tạo được bucket '%s': %s", settings.s3_bucket, exc)

    _s3_client = client
    return _s3_client


def _s3_put(key: str, data: bytes) -> str:
    _s3().put_object(Bucket=settings.s3_bucket, Key=key, Body=data)
    return key


def _s3_get(key: str) -> bytes:
    resp = _s3().get_object(Bucket=settings.s3_bucket, Key=key)
    return resp["Body"].read()


def _s3_delete_prefix(prefix: str) -> None:
    """Xoá mọi object có key bắt đầu bằng prefix (best-effort)."""
    client = _s3()
    paginator = client.get_paginator("list_objects_v2")
    to_delete: list[dict] = []
    for page in paginator.paginate(Bucket=settings.s3_bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            to_delete.append({"Key": obj["Key"]})
            if len(to_delete) == 1000:  # giới hạn delete_objects mỗi lần
                client.delete_objects(
                    Bucket=settings.s3_bucket, Delete={"Objects": to_delete}
                )
                to_delete = []
    if to_delete:
        client.delete_objects(Bucket=settings.s3_bucket, Delete={"Objects": to_delete})


# --- Public API (backend-agnostic) --------------------------------------------

def put_bytes(key: str, data: bytes) -> str:
    """Ghi blob theo key. Trả về chính key đó (để lưu vào DB)."""
    if settings.storage_backend == "s3":
        return _s3_put(key, data)
    return _local_put(key, data)


def get_bytes(key: str) -> bytes:
    """Đọc blob theo key."""
    if settings.storage_backend == "s3":
        return _s3_get(key)
    return _local_get(key)


def delete_prefix(prefix: str) -> None:
    """Xoá mọi blob dưới prefix (PDF gốc + ảnh page của 1 document). Best-effort."""
    if settings.storage_backend == "s3":
        _s3_delete_prefix(prefix)
    else:
        _local_delete_prefix(prefix)
