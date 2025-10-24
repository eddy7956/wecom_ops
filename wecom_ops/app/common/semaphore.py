from app.core.redis import get_redis

def acquire_sem(key: str, ttl_s: int, capacity: int) -> bool:
    r = get_redis()
    r.setnx(key, capacity)
    r.expire(key, ttl_s)
    cur = int(r.get(key) or capacity)
    if cur <= 0:
        return False
    r.decr(key)
    r.expire(key, ttl_s)
    return True

def release_sem(key: str, capacity: int):
    r = get_redis()
    cur = int(r.get(key) or 0)
    if cur < capacity:
        r.incr(key)
