# app/common/response.py
from flask import jsonify, request

def ok(data=None, status=200, headers=None):
    payload = {"ok": True, "data": data if data is not None else {}}
    resp = jsonify(payload); resp.status_code = status
    if headers:
        for k, v in headers.items(): resp.headers[k] = v
    rid = request.headers.get("X-Request-Id")
    if rid: resp.headers["X-Request-Id"] = rid
    return resp

def err(code: str, message: str, status=400, extra: dict | None = None):
    payload = {"ok": False, "error": {"code": code, "message": message}}
    if extra: payload["error"].update(extra)
    resp = jsonify(payload); resp.status_code = status
    rid = request.headers.get("X-Request-Id")
    if rid: resp.headers["X-Request-Id"] = rid
    return resp
