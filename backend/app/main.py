"""FastAPI app: CORS, khởi tạo DB, include routers, health check."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db
from app.retrieval.mcp import client as retrieval_client
from app.routers import documents, playground

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="RAG Platform API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev-simple; siết lại ở production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(playground.router)


@app.on_event("startup")
async def _startup():
    init_db()
    # Retrieval Engine chạy như service riêng (xem docker-compose.yml, service
    # retrieval-mcp) — backend chỉ nói chuyện với nó qua MCP, giữ 1 session sống
    # suốt vòng đời app thay vì mở/đóng kết nối mỗi request.
    await retrieval_client.connect()


@app.on_event("shutdown")
async def _shutdown():
    await retrieval_client.close()


@app.get("/api/health")
def health():
    return {"status": "ok"}
