from flask import Blueprint, request, jsonify, g
import re, traceback, sys
from app.core.db import get_mysql_conn as get_conn  # 统一别名

bp = Blueprint("identity_api", __name__, url_prefix="/api/v1/identity")

def j(payload, http=200):
    resp = jsonify(payload)
    try:
        resp.headers.setdefault("X-Request-Id", getattr(g, "trace_id", ""))
    except Exception:
        pass
    return resp, http

def _norm_mobile(s: str) -> str:
    """仅保留数字；若带 86 且长度>11，去掉前缀 86"""
    digits = re.sub(r"\D+", "", s or "")
    if digits.startswith("86") and len(digits) > 11:
        digits = digits[2:]
    return digits

def _get_val(row, *keys_or_idx):
    """
    同时兼容 元组/列表/字典 的取值。
    传入一组 key/idx，按顺序尝试，第一个命中就返回，否则返回 None。
    """
    if row is None:
        return None
    # dict
    if hasattr(row, "keys"):
        for k in keys_or_idx:
            if k in row:
                return row[k]
        return None
    # 序列
    for k in keys_or_idx:
        if isinstance(k, int):
            try:
                return row[k]
            except Exception:
                pass
    return None

@bp.post("/resolve-mobiles")
def resolve_mobiles():
    try:
        body = request.get_json(silent=True) or {}
        mobiles = body.get("mobiles") or []
        norm = [_norm_mobile(x) for x in mobiles]
        norm = [x for x in norm if x]  # 去空

        if not norm:
            return j({"ok": True, "data": {"mapped": [], "unmatched": []}})

        placeholders = ",".join(["%s"] * len(norm))
        sql = f"""
            SELECT mobile_std, external_userid
            FROM wecom_ops.vw_mobile_to_external
            WHERE mobile_std IN ({placeholders})
        """
        conn = get_conn()
        mapped_dict = {}
        with conn.cursor() as cur:
            cur.execute(sql, norm)
            rows = cur.fetchall()
            for r in rows:
                mobile_std = _get_val(r, "mobile_std", 0)
                external_userid = _get_val(r, "external_userid", 1)
                if not mobile_std or not external_userid:
                    continue
                mapped_dict.setdefault(mobile_std, set()).add(external_userid)

        mapped = [{"mobile": m, "external_userid": sorted(list(v))[0]}
                  for m, v in mapped_dict.items()]
        unmatched = sorted(set(norm) - set(mapped_dict.keys()))

        return j({"ok": True, "data": {"mapped": mapped, "unmatched": unmatched}})
    except Exception as e:
        return j({"ok": False, "error": {"code": "INTERNAL_ERROR",
                                         "message": str(e),
                                         "detail": traceback.format_exc()}}, 500)

@bp.get("/mapping")
def mapping():
    try:
        eid = (request.args.get("external_userid") or "").strip()
        if not eid:
            return j({"ok": False, "error": {"code": "VALIDATION_ERROR",
                                             "message": "external_userid required"}}, 400)

        conn = get_conn()
        name, unionid = None, None
        mobiles = []

        with conn.cursor() as cur:
            # 使用视图全景数据（ANY_VALUE 保证可聚合；别名用于 DictCursor 友好取值）
            cur.execute("""
                SELECT ANY_VALUE(ext_name) AS name,
                       ANY_VALUE(unionid)  AS unionid
                FROM wecom_ops.vw_vip_panorama
                WHERE external_userid=%s
            """, (eid,))
            row = cur.fetchone()
            if row:
                name    = _get_val(row, "name", 0)
                unionid = _get_val(row, "unionid", 1)

            # 提取该 EID 的所有标准化手机号
            cur.execute("""
                SELECT DISTINCT mobile_std
                FROM wecom_ops.vw_mobile_to_external
                WHERE external_userid=%s
            """, (eid,))
            rows = cur.fetchall()
            mobiles = [ _get_val(r, "mobile_std", 0) for r in rows if _get_val(r, "mobile_std", 0) ]

        return j({"ok": True, "data": {
            "external_userid": eid,
            "name": name,
            "unionid": unionid,
            "mobiles": mobiles
        }})
    except Exception as e:
        return j({"ok": False, "error": {"code": "INTERNAL_ERROR",
                                         "message": str(e),
                                         "detail": traceback.format_exc()}}, 500)
