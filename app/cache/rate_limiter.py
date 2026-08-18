"""Redis-based rate limiter"""
import time
from app.cache.redis import get_redis


class RedisRateLimiter:
    def __init__(self, key_prefix="ratelimit"):
        self.prefix = key_prefix

    def check(self, client_id: str, max_requests: int = 60, window: int = 60) -> tuple[bool, int]:
        """Check if request is allowed. Returns (allowed, retry_after)"""
        try:
            r = get_redis()
            key = f"{self.prefix}:{client_id}"
            now = int(time.time())
            window_start = now - window
            r.zremrangebyscore(key, 0, window_start)
            count = r.zcard(key) or 0
            if count >= max_requests:
                oldest = r.zrange(key, 0, 0, withscores=True)
                retry_after = int(window - (now - oldest[0][1])) if oldest else window
                return False, retry_after
            r.zadd(key, {str(now): now})
            r.expire(key, window)
            return True, 0
        except Exception:
            return True, 0  # fallback: allow request


rate_limiter = RedisRateLimiter()