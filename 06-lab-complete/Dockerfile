# ============================================================
# Dockerfile production — multi-stage (tiêu chí 1)
#   • Stage builder: tạo virtualenv và cài dependencies
#   • Stage runtime: chỉ copy virtualenv + code, chạy bằng user non-root
#   • CMD dùng exec form qua `sh -c "exec ..."` để uvicorn là PID 1,
#     nhận SIGTERM khi `docker stop` và tự shutdown êm
# ============================================================

# ──────────── STAGE 1: builder ────────────
FROM python:3.11-slim AS builder

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# ──────────── STAGE 2: runtime ────────────
FROM python:3.11-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# User không có quyền root
RUN groupadd -r app && useradd -r -g app -d /app -s /usr/sbin/nologin app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY app ./app
COPY utils ./utils

USER app

EXPOSE 8000

# Docker tự kiểm tra /health định kỳ
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Lắng nghe theo biến PORT (Railway/Render cấp PORT khi deploy)
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
