# MLflow server + Postgres driver + S3 client (cho RustFS artifact store).
# Image chính thức của MLflow không kèm psycopg2/boto3 nên tự build.
FROM python:3.11-slim

RUN pip install --no-cache-dir \
    "mlflow==3.14.0" \
    "psycopg2-binary==2.9.10" \
    "boto3==1.35.71"

EXPOSE 5000

# command được override trong docker-compose.yml
ENTRYPOINT []
