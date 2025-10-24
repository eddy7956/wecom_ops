# app/wecom/signature.py
import os, hashlib
from flask import Request

def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

def verify_callback_signature(req: Request) -> tuple[bool, str | None]:
    """返回 (ok, echostr_if_any)。GET 用于URL校验（原样回显 echostr），POST 仅校验签名。"""
    token = os.getenv("WECOM_CALLBACK_TOKEN", "")
    if not token:
        return False, None
    timestamp = req.args.get("timestamp", "")
    nonce     = req.args.get("nonce", "")
    echostr   = req.args.get("echostr")
    signature = req.args.get("msg_signature") or req.args.get("signature")  # 视回调类型而定

    parts = [token, timestamp, nonce]
    if echostr:  # GET 验证包含 echostr
        parts.append(echostr)
    calc = _sha1("".join(sorted(parts)))
    return (calc == signature, echostr)
