"""Redis-based rate limiter。Redis 不可用时返回 None，由调用方回退到进程内限流。"""
from __future__ import annotations

import time
import uuid
from typing import Optional

from app.config import settings


class RedisRateLimiter:
    def __init__(self, key_prefix: str = "ratelimit"):
        self.prefix = key_prefix

    def check(self, client_id: str, max_requests: int = 60, window: int = 60) -> Optional[tuple[bool, int]]:
        """Check if request is allowed. Returns (allowed, retry_after)，失败返回 None。"""
        try:
            import redis as redis_lib

            r = redis_lib.Redis.from_url(
                settings.redis_url or "redis://localhost:6379/0",
                decode_responses=True,
                socket_timeout=0.3,
                socket_connect_timeout=0.3,
            )
            try:
                key = f"{self.prefix}:{client_id}"
                now = time.time()
                window_start = now - window
                r.zremrangebyscore(key, 0, window_start)
                count = int(r.zcard(key) or 0)
                if count >= max_requests:
                    oldest = r.zrange(key, 0, 0, withscores=True)
                    retry_after = int(window - (now - oldest[0][1])) if oldest else window
                    return False, max(1, retry_after)
                r.zadd(key, {f"{now:.6f}:{uuid.uuid4().hex[:8]}": now})
                r.expire(key, window)
                return True, 0
            finally:
                r.close()
        except Exception:
            return None


rate_limiter = RedisRateLimiter()
