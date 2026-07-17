# Infra stack

MLflow tracking server backed by **Postgres** (metadata) and **RustFS** (S3-compatible artifact store).

## Chạy

```bash
cd infra
cp .env.example .env      # đổi RUSTFS secrets nếu cần
docker compose up --build
```

| Service        | URL                     | Ghi chú                          |
| -------------- | ----------------------- | -------------------------------- |
| MLflow UI      | http://localhost:5000   | tracking + artifact serving      |
| RustFS Console | http://localhost:9001   | login bằng RUSTFS_ACCESS/SECRET  |
| RustFS S3 API  | http://localhost:9000   | endpoint S3                      |
| Postgres       | localhost:5432          | db `mlflow`                      |

## Kết nối từ code

```python
import mlflow
mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("advanced-rag")
# Artifacts đi qua MLflow server (--serve-artifacts) → RustFS.
# Client không cần AWS credentials.
```

## Thành phần

- **postgres** — `backend-store-uri`, lưu experiments/runs/params/metrics.
- **rustfs** — object storage cho artifacts; MLflow nói chuyện qua S3 protocol
  (`MLFLOW_S3_ENDPOINT_URL` + `AWS_*`).
- **createbuckets** — one-shot dùng `mc` tạo bucket `mlflow` rồi thoát.
- **mlflow** — server build từ `mlflow.Dockerfile` (kèm psycopg2 + boto3),
  chạy với `--serve-artifacts` để client không cần S3 credentials.

## Lưu ý

- Data giữ trong named volumes `postgres_data`, `rustfs_data`.
- Đây là stack tách biệt với `../docker-compose.yml` (app RAG); chạy độc lập.
- Đổi `RUSTFS_SECRET_KEY` trước khi dùng ngoài môi trường local.
