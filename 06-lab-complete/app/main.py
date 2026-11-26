"""
Production AI Agent — Part 6 Final Project

Chạy:  uvicorn app.main:app --host 0.0.0.0 --port 8000
Kiểm tra: python check_production_ready.py
"""
import json
import logging
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_budget, record_cost
from app.rate_limiter import check_rate_limit
from app.redis_client import redis_healthy
from utils.mock_llm import ask as llm_ask


# ──────────────────────────────────────────────────────────
# Structured logging (tiêu chí 10)
# Mỗi dòng log là một JSON object. Dữ liệu thêm vào đi qua extra={"data": {...}}
# ──────────────────────────────────────────────────────────
class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "ts": self.formatTime(record),
            "lvl": record.levelname,
            "event": record.getMessage(),
        }
        payload.update(getattr(record, "data", {}))
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
logger = logging.getLogger("agent")


# ──────────────────────────────────────────────────────────
# Lifespan: log khi khởi động và tắt
# Khi nhận SIGTERM, uvicorn tự ngừng nhận request mới,
# chờ request đang chạy xong rồi thoát với exit code 0.
# ──────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", extra={"data": {"env": settings.environment, "port": settings.port}})
    yield
    logger.info("shutdown", extra={"data": {"event_type": "graceful"}})


app = FastAPI(title="Production AI Agent", lifespan=lifespan)


@app.middleware("http")
async def access_log(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    ms = round((time.perf_counter() - start) * 1000, 1)
    logger.info("request", extra={"data": {
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "ms": ms,
    }})
    return response


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


# ──────────────────────────────────────────────────────────
# Health & readiness (tiêu chí 4, 5)
# ──────────────────────────────────────────────────────────
@app.get("/health")
def health():
    # Luôn 200 khi process còn chạy, kể cả khi Redis chết
    return {"status": "ok"}


@app.get("/ready")
def ready():
    # 503 khi Redis không kết nối được
    if not redis_healthy():
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready"}


# ──────────────────────────────────────────────────────────
# Endpoint chính
# Thứ tự kiểm tra: API key (401) → rate limit (429) → budget (402) → gọi LLM
# ──────────────────────────────────────────────────────────
@app.post("/ask")
def ask(body: AskRequest, api_key: str = Depends(verify_api_key)):
    check_rate_limit(api_key)
    check_budget()

    answer = llm_ask(body.question)

    # Ước lượng token theo số từ (đủ cho bài lab, không cần tokenizer thật)
    input_tokens = len(body.question.split())
    output_tokens = len(answer.split())
    cost = record_cost(input_tokens, output_tokens)

    logger.info("llm_call", extra={"data": {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost,
    }})
    return {"question": body.question, "answer": answer}
