"""Redis connection manager — 惰性连接，开发环境无 Redis 时不阻断启动。"""
from app.config import settings

_redis_client = None


def get_redis():
    global _redis_client
    if _redis_client is None:
        import redis
        _redis_client = redis.Redis.from_url(
            settings.redis_url or "redis://localhost:6379/0",
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30,
        )
    return _redis_client


def close_redis():
    global _redis_client
    if _redis_client:
        try:
            _redis_client.close()
        except Exception:
            pass
        _redis_client = None


def ping_redis() -> bool:
    try:
        return bool(get_redis().ping())
    except Exception:
        return False


class _LazyRedis:
    def __getattr__(self, name):
        return getattr(get_redis(), name)


redis_client = _LazyRedis()
