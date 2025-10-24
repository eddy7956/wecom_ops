import os, json, time
import redis as _redis

def _r():
    return _redis.Redis(host=os.getenv("REDIS_HOST","127.0.0.1"),
                        port=int(os.getenv("REDIS_PORT","6379")),
                        db=int(os.getenv("REDIS_DB","0")),
                        decode_responses=True)

def get_with_singleflight(key, loader, soft_ttl_s=300, hard_ttl_s=900):
    r = _r(); now = int(time.time()); mk = key+":meta"
    val = r.get(key); meta = r.get(mk)
    if val and meta:
        meta = json.loads(meta)
        age = now - meta["ts"]
        if age < hard_ttl_s:
            if age > soft_ttl_s and r.setnx(key+":lock","1"):
                r.expire(key+":lock", 30)
                try:
                    fresh = loader()
                    r.set(key, json.dumps(fresh), ex=hard_ttl_s)
                    r.set(mk, json.dumps({"ts": now}), ex=hard_ttl_s)
                finally:
                    r.delete(key+":lock")
            return json.loads(val)
    if r.setnx(key+":lock","1"):
        r.expire(key+":lock", 30)
        try:
            fresh = loader()
            r.set(key, json.dumps(fresh), ex=hard_ttl_s)
            r.set(mk, json.dumps({"ts": now}), ex=hard_ttl_s)
            return fresh
        finally:
            r.delete(key+":lock")
    time.sleep(0.2)
    return json.loads(r.get(key) or "null")
