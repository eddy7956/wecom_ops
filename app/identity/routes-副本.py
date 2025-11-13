from flask import Blueprint, request, jsonify, g
from app.core.db import get_mysql_conn
import re, json

bp = Blueprint("identity", __name__, url_prefix="/api/v1/identity")

def _ok(payload, status=200):
    resp = jsonify({"ok": True, "data": payload})
    resp.status_code = status
    resp.headers["X-Request-Id"] = getattr(g, "trace_id", "")
    return resp

def _err(code, msg, status=422, detail=None):
    err = {"code": code, "message": msg}
    if detail is not None: err["detail"] = detail
    resp = jsonify({"ok": False, "error": err})
    resp.status_code = status
    resp.headers["X-Request-Id"] = getattr(g, "trace_id", "")
    return resp

def _norm_mobile(x):
    return re.sub(r"\D", "", str(x or ""))

@bp.post("/resolve-mobiles")
def resolve_mobiles():
    try:
        body = request.get_json(force=True)
    except Exception as e:
        return _err("VALIDATION_ERROR", "invalid JSON body", detail=str(e))
    if not isinstance(body, dict) or not isinstance(body.get("mobiles"), list):
        return _err("VALIDATION_ERROR", "body.mobiles must be an array")

    # 归一化（只保留数字），去重，过滤空
    raw_list = [str(x) for x in body["mobiles"] if str(x).strip()]
    norm_list = []
    seen = set()
    for m in raw_list:
        nm = _norm_mobile(m)
        if nm and nm not in seen:
            seen.add(nm); norm_list.append(nm)

    if not norm_list:
        return _ok({"mapped": [], "unmatched": []})

    conn = get_mysql_conn()
    mapped = {}
    placeholders = ",".join(["%s"] * len(norm_list))

    # 统一查询：先查数组 path，再查若干单值 path
    with conn.cursor() as cur:
        sqls, params = [], []
        # 1) 数组 $.mobiles[*]
        sqls.append(f"""
          SELECT DISTINCT REGEXP_REPLACE(jt.mobile,'\\D','') AS mobile, ec.external_userid
          FROM ext_contact ec,
               JSON_TABLE(JSON_EXTRACT(ec.detail_json, '$.mobiles'),
                          '$[*]' COLUMNS(mobile VARCHAR(64) PATH '$')) jt
          WHERE jt.mobile IS NOT NULL
            AND REGEXP_REPLACE(jt.mobile,'\\D','') IN ({placeholders})
        """)
        params += norm_list

        # 2) 常见单值路径（逐个路径 UNION）
        paths = ['$.mobile','$.phone','$.telephone','$.profile.mobile','$.external_profile.mobile']
        for p in paths:
            sqls.append(f"""
              SELECT DISTINCT
                     REGEXP_REPLACE(JSON_UNQUOTE(JSON_EXTRACT(ec.detail_json, %s)),'\\D','') AS mobile,
                     ec.external_userid
              FROM ext_contact ec
              WHERE JSON_EXTRACT(ec.detail_json, %s) IS NOT NULL
                AND REGEXP_REPLACE(JSON_UNQUOTE(JSON_EXTRACT(ec.detail_json, %s)),'\\D','') IN ({placeholders})
            """)
            params += [p, p, p] + norm_list

        cur.execute(" UNION ALL ".join(sqls), params)
        for row in cur.fetchall():
            mob = row["mobile"]; eid = row["external_userid"]
            if mob and eid and mob in norm_list and mob not in mapped:
                mapped[mob] = eid

    mapped_items = [{"mobile": m, "external_userid": mapped[m]} for m in norm_list if m in mapped]
    unmatched = [m for m in norm_list if m not in mapped]
    return _ok({"mapped": mapped_items, "unmatched": unmatched})

@bp.get("/mapping")
def mapping():
    eid = (request.args.get("external_userid") or "").strip()
    if not eid:
        return _err("VALIDATION_ERROR", "query param external_userid is required")

    conn = get_mysql_conn()
    with conn.cursor() as cur:
        cur.execute("""
          SELECT external_userid, name, unionid,
                 JSON_EXTRACT(detail_json,'$.mobiles') AS mobiles_json,
                 JSON_EXTRACT(detail_json,'$.mobile')  AS mobile_json
          FROM ext_contact
          WHERE external_userid = %s
          LIMIT 1
        """, [eid])
        row = cur.fetchone()

    if not row:
        return _err("NOT_FOUND", "external_userid not found", status=404)

    # 尝试解析 mobiles；若没有，则回退到 mobile_json
    mobiles = []
    try:
        v = row.get("mobiles_json")
        if isinstance(v, (bytes, bytearray)): v = v.decode()
        if v: mobiles = json.loads(v)
        if isinstance(mobiles, str): mobiles = [mobiles]
    except Exception:
        mobiles = []

    if not mobiles:
        try:
            v = row.get("mobile_json")
            if isinstance(v, (bytes, bytearray)): v = v.decode()
            if v:
                one = json.loads(v)
                if isinstance(one, str): mobiles = [one]
        except Exception:
            pass

    return _ok({
        "external_userid": row["external_userid"],
        "name": row["name"],
        "unionid": row["unionid"],
        "mobiles": mobiles or []
    })
