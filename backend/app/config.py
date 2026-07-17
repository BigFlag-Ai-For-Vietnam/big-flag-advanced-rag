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

    # --- Retrieval Engine (LangGraph + MCP) ---
    # URL của MCP server (Retrieval Engine), chạy như service riêng — xem docker-compose.yml.
    retrieval_mcp_url: str = "http://localhost:8100/mcp"
    # Số bước lặp tối đa của ReAct subgraph (agent<->tools) — chặn loop vô hạn/tốn phí.
    retrieval_agent_max_steps: int = 6
    # Bật/tắt từng node deterministic (normalize/rewrite/rerank) để so sánh ảnh hưởng —
    # tắt (false) khiến node tương ứng thành no-op/passthrough, không đổi shape của graph.
    retrieval_enable_normalize: bool = True
    retrieval_enable_rewrite: bool = True
    retrieval_enable_rerank: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
