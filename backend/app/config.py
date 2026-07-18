"""Cấu hình ứng dụng đọc từ biến môi trường (.env) qua pydantic-settings."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- FPT AI Marketplace (OpenAI-compatible) ---
    fpt_api_key: str = ""
    fpt_base_url: str = "https://mkp-api.fptcloud.com"
    # Các model ID phải lấy đúng từ marketplace — không hardcode giá trị thật ở đây.
    fpt_vlm_model: str = ""          # ID model vision (GLM) đọc ảnh page
    fpt_chat_model: str = ""         # ID model chat (contextual + QA)
    fpt_embed_model: str = ""        # ID model embedding
    embed_dim: int = 1024            # PHẢI khớp số chiều vector của model embedding thực tế
    fpt_enable_prompt_cache: bool = False
    # GLM-5.x là model reasoning: mặc định "nghĩ" trước khi trả lời, ngốn hết token budget
    # và trả content rỗng nếu max_tokens thấp. Tắt thinking cho tác vụ RAG (contextual + QA)
    # -> rẻ, nhanh, output ổn định. Truyền qua extra_body chat_template_kwargs.enable_thinking.
    fpt_disable_thinking: bool = True
    contextual_max_tokens: int = 500   # token tối đa cho câu định vị (contextual chunking)
    catalog_max_tokens: int = 1500     # token tối đa cho cây entities (catalog) mỗi đơn vị
    # Nguồn build catalog:
    #  - "chunks" (mặc định): trích từ final_content (đã contextual) — mỗi mảnh self-contained
    #    nhờ câu định vị, gán facet đúng kể cả khi section kéo dài qua nhiều trang / không header.
    #  - "pages": trích từ parsed_text từng trang — giữ heading/layout gốc.
    catalog_source: str = "chunks"

    # Giới hạn gọi API ngoài
    llm_timeout: float = 120.0
    llm_max_retries: int = 3
    vlm_max_concurrency: int = 4     # số page parse song song tối đa
    # Nếu VLM trả rỗng cho 1 trang, dùng text-layer của PDF (page.extract_text) làm dự phòng.
    # Giúp không bị "document rỗng" khi model không hỗ trợ vision hoặc PDF có sẵn text.
    parse_text_fallback: bool = True

    # --- Qdrant ---
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "rag_chunks"

    # --- Storage / DB ---
    db_url: str = "sqlite:///./data/rag.db"
    data_dir: str = "./data"         # gốc lưu blob khi storage_backend="local"
    # Backend lưu blob (PDF gốc + ảnh page): "local" (đĩa dưới data_dir) hoặc "s3" (RustFS).
    storage_backend: str = "local"
    # Cấu hình S3/RustFS — chỉ dùng khi storage_backend="s3".
    s3_endpoint_url: str = "http://localhost:9000"   # RustFS S3 API (trong infra compose: http://rustfs:9000)
    s3_access_key: str = "rustfsadmin"
    s3_secret_key: str = "rustfsadmin"
    s3_bucket: str = "rag-documents"                 # tách biệt bucket "mlflow" của infra
    s3_region: str = "us-east-1"

    # --- Chunking ---
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # --- Eval / MLflow ---
    # Mặc định localhost phục vụ CLI chạy trên host; backend chạy trong container
    # PHẢI override (http://host.docker.internal:5000 hoặc mạng compose chung) — xem FR-13.
    mlflow_tracking_uri: str = "http://localhost:5000"
    mlflow_experiment: str = "advanced-rag-eval"
    # Rỗng -> fallback fpt_chat_model tại nơi dùng (judge factory trong llm_client, T05).
    # KHÔNG resolve fallback ở đây: giữ "" để nơi dùng biết là chưa override.
    eval_judge_model: str = ""
    eval_max_workers: int = 4        # chặn song song mọi lời gọi LLM của eval (rate-limit FPT)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
