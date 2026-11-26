"""
Rate limiting (tiêu chí 7).

Yêu cầu:
  • Mỗi API key tối đa RATE_LIMIT_PER_MINUTE request trong 60 giây (sliding window)
  • Vượt giới hạn → HTTP 429, nên kèm header Retry-After
  • State lưu trong Redis để mọi worker / instance dùng chung và vẫn còn sau khi
    restart agent (script chấm sẽ restart agent để kiểm tra)

Cách làm (sliding window bằng Redis sorted set):
  • Mỗi request là một phần tử trong sorted set, điểm số = thời điểm request
  • Xóa phần tử cũ hơn 60 giây → đếm số phần tử còn lại → nếu đủ giới hạn thì 429
"""
import hashlib
import time
import uuid

from fastapi import HTTPException

from app.config import settings
from app.redis_client import r

WINDOW_SECONDS = 60


def check_rate_limit(key: str) -> None:
    now = time.time()
    # Băm key API để không lưu key thật trong Redis
    hashed = hashlib.sha256(key.encode()).hexdigest()[:16]
    redis_key = f"ratelimit:{hashed}"

    # 1. Xóa các request đã ra khỏi cửa sổ 60 giây và đếm số request còn lại
    pipe = r.pipeline()
    pipe.zremrangebyscore(redis_key, 0, now - WINDOW_SECONDS)
    pipe.zcard(redis_key)
    _, count = pipe.execute()

    # 2. Vượt giới hạn → 429 kèm Retry-After
    if count >= settings.rate_limit_per_minute:
        oldest = r.zrange(redis_key, 0, 0, withscores=True)
        retry_after = 1
        if oldest:
            retry_after = max(1, int(oldest[0][1] + WINDOW_SECONDS - now) + 1)
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )

    # 3. Ghi nhận request này
    pipe = r.pipeline()
    pipe.zadd(redis_key, {f"{now}:{uuid.uuid4().hex}": now})
    pipe.expire(redis_key, WINDOW_SECONDS)
    pipe.execute()
