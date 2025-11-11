# -*- coding: utf-8 -*-
import os, time, json, threading, requests, random
_QY = "https://qyapi.weixin.qq.com"
_tok_lock = threading.Lock()
_tok_cache = {}

def _now(): return int(time.time())
def _ttl_left(expire_ts): return expire_ts - _now()

def _get_token(secret_env_key: str):
    global _tok_cache
    with _tok_lock:
        v = _tok_cache.get(secret_env_key)
        if v and _ttl_left(v[1]) > 120:
            return v[0]
    corpid = os.getenv("WECOM_CORP_ID"); secret = os.getenv(secret_env_key)
    if not (corpid and secret):
        raise RuntimeError(f"missing env WECOM_CORP_ID or {secret_env_key}")
    r = requests.get(f"{_QY}/cgi-bin/gettoken",
                     params={"corpid": corpid, "corpsecret": secret}, timeout=10)
    r.raise_for_status(); data = r.json()
    if data.get("errcode") != 0:
        raise RuntimeError(f"gettoken error: {data}")
    token = data["access_token"]; expire_in = data.get("expires_in", 7200)
    with _tok_lock:
        _tok_cache[secret_env_key] = (token, _now() + expire_in)
    return token

def _sleep_backoff(i, base=0.8, cap=8.0):
    time.sleep(min(cap, base*(2**i)) + random.random()*0.3)

def _pick_secret(path: str, explicit: str | None):
    if explicit:
        return explicit, False
    if path.startswith("/cgi-bin/externalcontact/"):
        return "WECOM_EXT_SECRET", False
    if path.startswith("/cgi-bin/kf/"):
        return "WECOM_KF_SECRET", False
    return "WECOM_CONTACTS_SECRET", True

def wecom_get(path: str, params: dict | None = None,
              secret_env_key: str | None = None,
              fallback_secret_env_key: str | None = None,
              max_retry: int = 5):
    assert path.startswith("/")
    params = params or {}
    use_key, allow_fallback = _pick_secret(path, secret_env_key)
    if allow_fallback and fallback_secret_env_key is None:
        fallback_secret_env_key = "WECOM_AGENT_SECRET"
    retry = 0; switched = False

    while True:
        token = _get_token(use_key)
        q = dict(params); q["access_token"] = token
        resp = requests.get(f"{_QY}{path}", params=q, timeout=15)

        if resp.status_code >= 500:
            if retry >= max_retry: resp.raise_for_status()
            _sleep_backoff(retry); retry += 1; continue

        data = resp.json(); ec = data.get("errcode", -1)
        if ec == 0:
            return data

        if ec in (40014, 42001, 40001):
            with _tok_lock:
                _tok_cache.pop(use_key, None)
            if retry >= max_retry:
                raise RuntimeError(f"token error: path={path} use_key={use_key} params={params} data={data}")
            _sleep_backoff(retry); retry += 1; continue

        if allow_fallback and ec in (48009, 48001) and not switched \
           and fallback_secret_env_key and os.getenv(fallback_secret_env_key):
            use_key = fallback_secret_env_key; switched = True
            _sleep_backoff(retry); retry += 1; continue

        if ec == 45009:
            if retry >= max_retry:
                raise RuntimeError(f"rate limit: path={path} use_key={use_key} params={params} data={data}")
            _sleep_backoff(retry); retry += 1; continue

        # 关键：把 path/params/secret 一起打出来
        raise RuntimeError(f"wecom GET error: path={path} use_key={use_key} params={params} data={data}")

