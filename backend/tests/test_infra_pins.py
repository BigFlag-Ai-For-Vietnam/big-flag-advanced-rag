"""Guard pin phiên bản MLflow trong infra (đọc file, không chạy docker)."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]  # backend/tests/ -> repo root


def test_mlflow_dockerfile_pin_and_docs():
    dockerfile = (REPO_ROOT / "infra" / "mlflow.Dockerfile").read_text(encoding="utf-8")
    assert "mlflow==3.14.0" in dockerfile
    assert "2.17.2" not in dockerfile  # pin cũ phải biến mất

    readme = (REPO_ROOT / "infra" / "README.md").read_text(encoding="utf-8")
    assert "Nâng cấp MLflow" in readme      # heading của section upgrade
    assert "pg_dump" in readme              # lệnh backup Postgres
    assert "mlflow db upgrade" in readme    # ghi chú schema migration
