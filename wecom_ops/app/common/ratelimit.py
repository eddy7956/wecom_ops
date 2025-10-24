import time
from app.core.redis import get_redis

def _now_ms():
    return int(time.time() * 1000)

def take_token(bucket_key: str, capacity: int, refill_per_sec: int) -> bool:
    r = get_redis()
    state = r.hgetall(bucket_key) or {}
    last_ms = int(state.get("last_ms", 0))
    tokens = int(state.get("tokens", capacity))
    now = _now_ms()
    elapsed = max(0, now - last_ms)
    refill = (elapsed * refill_per_sec) // 1000
    tokens = min(capacity, tokens + refill)
    if tokens <= 0:
        r.hset(bucket_key, mapping={"tokens": tokens, "last_ms": now})
        r.expire(bucket_key, 60)
        return False
    tokens -= 1
    r.hset(bucket_key, mapping={"tokens": tokens, "last_ms": now})
    r.expire(bucket_key, 60)
    return True
