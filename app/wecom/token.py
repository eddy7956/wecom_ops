# app/wecom/token.py
import os, time, random, hashlib
import requests
from app.core.redis import get_redis

def _key(agent_id: str) -> str:
    return f"wec:token:access:{agent_id}"

def get_access_token(agent_id: str | int) -> str:
    agent_id = str(agent_id)
    r = get_redis()
    k = _key(agent_id)
    val = r.get(k)
    if val:
        return val

    corp_id = os.getenv("WECOM_CORP_ID")
    secret  = os.getenv("WECOM_AGENT_SECRET")
    if not corp_id or not secret:
        raise RuntimeError("WECOM_CORP_ID/SECRET not configured")

    url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken"
    resp = requests.get(url, params={"corpid": corp_id, "corpsecret": secret}, timeout=5)
    data = resp.json()
    if data.get("errcode") != 0:
        raise RuntimeError(f"gettoken failed: {data}")

    token = data["access_token"]
    expires_in = int(data.get("expires_in", 7200))
    # 预留 300s 安全窗 + 抖动，防雪崩
    ttl = max(60, expires_in - 300 - random.randint(0, 60))
    r.setex(k, ttl, token)
    return token
