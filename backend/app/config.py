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
    data_dir: str = "./data"         # nơi lưu file PDF gốc + ảnh page tạm

    # --- Chunking ---
    chunk_size: int = 1000
    chunk_overlap: int = 200


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
