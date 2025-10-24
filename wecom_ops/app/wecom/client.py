# -*- coding: utf-8 -*-
import os, time, json, logging, threading
import requests
import redis as _redis

log = logging.getLogger(__name__)
_session = requests.Session()

def _r():
    try:
        return _redis.Redis(host=os.getenv("REDIS_HOST","127.0.0.1"),
                            port=int(os.getenv("REDIS_PORT","6379")),
                            db=int(os.getenv("REDIS_DB","0")),
                            decode_responses=True)
    except Exception:
        return None

def _token_bucket(key="wec:rl:pull", qps=8, burst=16):
    r = _r()
    if not r: return True
    now = int(time.time())
    cap = int(os.getenv("WECOM_PULL_BURST", burst))
    rate = float(os.getenv("WECOM_PULL_QPS", qps))
    tokens = float(r.get(key+":tokens") or cap)
    ts = int(r.get(key+":ts") or now)
    tokens = min(cap, tokens + (now - ts) * rate)
    if tokens < 1:
        time.sleep(1.0/max(rate,1))
        return _token_bucket(key, qps, burst)
    pipe = r.pipeline(True)
    pipe.set(key+":tokens", tokens - 1)
    pipe.set(key+":ts", now)
    pipe.execute()
    return True

_token_cache = {}
_lock = threading.Lock()

def get_access_token(scope="contacts"):
    with _lock:
        info = _token_cache.get(scope)
        if info and info["exp"] > time.time():
            return info["val"]
    corpid = os.getenv("WECOM_CORP_ID")
    if scope == "contacts":
        secret = os.getenv("WECOM_CONTACTS_SECRET")
    elif scope == "kf":
        secret = os.getenv("WECOM_KF_SECRET")
    else:
        secret = os.getenv("WECOM_EXT_SECRET")
    url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
    _token_bucket()
    resp = _session.get(url, params={"corpid": corpid, "corpsecret": secret}, timeout=(5,15))
    data = resp.json()
    if data.get("errcode") != 0:
        raise RuntimeError(f"gettoken failed: {data}")
    _token_cache[scope] = {"val": data["access_token"], "exp": time.time()+3600}
    return data["access_token"]

def wecom_get_json(path, scope="contacts", params=None):
    if params is None: params = {}
    params["access_token"] = get_access_token(scope)
    _token_bucket()
    r = _session.get(path, params=params, timeout=(5,30))
    data = r.json()
    if data.get("errcode") != 0:
        raise RuntimeError(f"wecom GET error: {data}")
    return data

def wecom_post_json(path, scope="ext", params=None, body=None):
    if params is None: params = {}
    params["access_token"] = get_access_token(scope)
    _token_bucket()
    r = _session.post(path, params=params, json=body or {}, timeout=(5,30))
    data = r.json()
    if data.get("errcode") != 0:
        raise RuntimeError(f"wecom POST error: {data}")
    return data
