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

    # --- Agentic planning (plan -> gather -> assess -> loop) ---
    # Bật planning: tách câu hỏi thành sub-goal, retrieve từng cái, kiểm tra coverage, lặp
    # tới khi đủ hoặc hết budget. Tắt -> 1 sub-goal = cả câu hỏi (retrieve 1 lần, không loop).
    retrieval_enable_planning: bool = True
    # Budget: số vòng gather->assess tối đa (mỗi vòng broaden các sub-goal còn thiếu).
    retrieval_max_hops: int = 3
    # Số chunk lấy cho mỗi sub-goal mỗi vòng gather.
    retrieval_per_subgoal_k: int = 4
    # Chặn số sub-goal do planner sinh ra (tránh nổ số lần gọi retrieve).
    retrieval_plan_max_subgoals: int = 6
    # Điểm tối thiểu để coi 1 chunk là bằng chứng (fallback heuristic khi assess LLM lỗi).
    retrieval_coverage_min_score: float = 0.35

    # --- Hybrid retrieval (dense Qdrant + sparse BM25, fuse RRF-lite) ---
    # Bật: mỗi lần search = dense (vector) + BM25 (keyword) rồi hợp nhất → vá ca tra
    # bảng/số/keyword mà dense yếu. Tắt -> dense-only như cũ.
    retrieval_enable_hybrid: bool = True
    # Trọng số dense khi fuse (0..1); phần còn lại (1-alpha) cho BM25.
    retrieval_hybrid_alpha: float = 0.5

    # --- Knowledge Graph (Neo4j) — đọc lúc query ---
    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = ""
    # Bật graph baseline trong retrieval engine — mặc định tắt, chỉ bật sau khi graph đã
    # build (graph_service.stats() không rỗng), tránh giai đoạn "bật nhưng graph rỗng".
    retrieval_enable_graph: bool = False
    retrieval_graph_citation_hops: int = 1
    retrieval_graph_concept_top_k: int = 5
    retrieval_graph_max_facts_per_subgoal: int = 6
    # Model embedding tiếng Việt cho similarity thấp hơn trực giác (calibrate thật ở PoC:
    # 1 cặp chắc chắn đúng chỉ đạt ~0.62) — KHÔNG dùng threshold mặc định kiểu 0.8.
    retrieval_graph_concept_embedding_threshold: float = 0.65

    # --- Knowledge Graph build (LightRAG + ontology) — chạy lúc ingest, nền, không chặn Qdrant ---
    kg_enable_build: bool = False
    kg_categories: list[str] = ["tuan_thu"]     # ontology hiện chỉ verify đúng domain này
    # PHẢI = 1 (đã verify bằng chạy thật): LightRAG's document-processing queue
    # (`pipeline_status["busy"]`) là singleton theo `workspace` (mặc định "" — dùng chung
    # cho MỌI document, bắt buộc vì cần 1 graph chung cross-document, không thể tách
    # workspace riêng từng doc). >1 build đồng thời -> document "thua" cuộc đua chỉ tự
    # đánh dấu "queued" trong pipeline_status rồi RETURN ngay, không hề tự chạy loop xử lý
    # queue của chính nó (loop đó thuộc về LightRAG instance khác, doc_status riêng) ->
    # 0 entity được extract cho document đó dù ainsert() "thành công" không lỗi gì.
    kg_max_concurrent_builds: int = 1

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
