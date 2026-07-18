# Infra stack

**Qdrant** (vector DB của app RAG) + MLflow tracking server backed by **Postgres** (metadata) and **RustFS** (S3-compatible artifact store).

## Chạy

```bash
cd infra
cp .env.example .env      # đổi RUSTFS secrets nếu cần
docker compose up --build
```

| Service        | URL                     | Ghi chú                          |
| -------------- | ----------------------- | -------------------------------- |
| nginx          | http://localhost / https://localhost | cửa vào duy nhất của app: serve frontend + proxy `/api`+`/docs` về backend (self-signed cert cho 443) |
| Qdrant         | http://localhost:6333   | vector DB (dashboard: `/dashboard`) |
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

- **qdrant** — vector DB của app RAG (backend app nối vào qua network `rag-infra`).
- **postgres** — `backend-store-uri`, lưu experiments/runs/params/metrics.
- **rustfs** — object storage cho artifacts; MLflow nói chuyện qua S3 protocol
  (`MLFLOW_S3_ENDPOINT_URL` + `AWS_*`).
- **createbuckets** — one-shot dùng `mc` tạo bucket `mlflow` rồi thoát.
- **mlflow** — server build từ `mlflow.Dockerfile` (kèm psycopg2 + boto3),
  chạy với `--serve-artifacts` để client không cần S3 credentials.

## Lưu ý

- Data giữ trong named volumes `qdrant_data`, `postgres_data`, `rustfs_data`.
- Network compose có tên cố định **`rag-infra`** (attachable): app stack
  (`../docker-compose.yml`) nối backend vào đây để gọi `qdrant:6333` / `mlflow:5000` /
  `rustfs:9000` theo service name → **chạy stack này trước** khi up app stack.
- Đổi `RUSTFS_SECRET_KEY` trước khi dùng ngoài môi trường local.

## Nâng cấp MLflow (2.17 → 3.14)

MLflow 3.14 là điều kiện tiên quyết cho eval-rag: `mlflow.genai.datasets`,
trace expectations, và Review Queues (dùng ở M4/M5) chỉ có ở MLflow ≥3.14.
Stack hiện tại pin `mlflow==3.14.0` trong `mlflow.Dockerfile`.

### 1. Backup trước khi nâng cấp

Luôn backup **cả hai**: dump logic (khôi phục nhanh, gọn) và snapshot volume thô
(khôi phục nguyên trạng nếu dump lỗi).

```bash
# Logical dump (khôi phục bằng psql)
docker compose exec postgres pg_dump -U mlflow -d mlflow > mlflow-backup-$(date +%F).sql

# Snapshot volume thô (khôi phục = giải nén đè lại)
docker compose stop mlflow postgres
docker run --rm -v infra_postgres_data:/data -v "$PWD":/backup alpine \
  tar czf /backup/postgres_data-$(date +%F).tgz -C /data .
docker compose start postgres
```

### 2. Schema migration

MLflow 3.x migrate schema tracking qua Alembic. Lần chạy đầu với image mới,
server có thể tự động nâng cấp hoặc từ chối khởi động và yêu cầu migrate thủ công:

```bash
docker compose run --rm mlflow \
  mlflow db upgrade postgresql://mlflow:mlflow@postgres:5432/mlflow
```

(thông tin đăng nhập/db lấy từ `infra/.env`, mặc định như trên). Sau đó chạy
`docker compose up --build mlflow` và kiểm tra UI tại `http://localhost:5000`
vẫn liệt kê đầy đủ experiments/runs cũ.

### 3. Rollback

Stack này **không phải production**: nếu nâng cấp lỗi, `docker compose down`,
khôi phục volume `infra_postgres_data` từ file `.tgz` (hoặc `psql < mlflow-backup-*.sql`
vào volume mới), revert pin trong `mlflow.Dockerfile` về `2.17.2`, rồi build lại.

**Lưu ý quan trọng**: schema đã migrate lên 3.14 **không** đọc được bởi MLflow 2.17 —
đây là lý do backup ở bước 1 là bắt buộc trước khi nâng cấp.
