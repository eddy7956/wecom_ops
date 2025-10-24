import os
from redis import Redis, ConnectionPool

_pool = None

def get_redis() -> Redis:
    global _pool

    # 优先支持 REDIS_URL（如 redis://127.0.0.1:6379/0）
    url = os.getenv("REDIS_URL", "").strip()
    if url:
        return Redis.from_url(url, decode_responses=True)

    host = os.getenv("REDIS_HOST", "127.0.0.1")
    port = int(os.getenv("REDIS_PORT", "6379"))
    db   = int(os.getenv("REDIS_DB", "0"))
    # 只有在密码“非空”时才传入，从而避免对无密码实例执行 AUTH
    pwd  = os.getenv("REDIS_PASSWORD", "").strip() or None

    if _pool is None:
        _pool = ConnectionPool(
            host=host, port=port, db=db, password=pwd,
            decode_responses=True, socket_connect_timeout=2
        )
    return Redis(connection_pool=_pool)
