from app.core.redis import get_redis

def try_mark_once(key: str, ttl_s: int) -> bool:
    r = get_redis()
    ok = r.set(name=key, value="1", nx=True, ex=ttl_s)
    return bool(ok)
