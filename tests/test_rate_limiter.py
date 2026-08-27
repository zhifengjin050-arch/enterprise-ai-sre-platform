"""Redis 限流器回退行为"""
from app.cache.rate_limiter import RedisRateLimiter


def test_rate_limiter_falls_back_when_redis_down(monkeypatch):
    limiter = RedisRateLimiter()
    monkeypatch.setattr("app.config.settings.redis_url", "redis://127.0.0.1:1/0")
    assert limiter.check("127.0.0.1", max_requests=1, window=60) is None
