from flask import Blueprint, request, jsonify, g
from app.core.db import get_mysql_conn
from datetime import datetime

bp = Blueprint("ext_v1", __name__, url_prefix="/api/v1/ext")

def _ok(payload, status=200):
    from flask import make_response
    resp = make_response(jsonify({"ok": True, "data": payload}), status)
    resp.headers["X-Request-Id"] = getattr(g, "trace_id", "")
    return resp

def _err(code, msg, status=422, detail=None):
    from flask import make_response
    e = {"code": code, "message": msg}
    if detail is not None: e["detail"] = detail
    resp = make_response(jsonify({"ok": False, "error": e}), status)
    resp.headers["X-Request-Id"] = getattr(g, "trace_id", "")
    return resp

def _parse_list(args, name):
    vals = args.getlist(name)
    if len(vals)==1 and ',' in (vals[0] or ''):
        vals = [v.strip() for v in vals[0].split(',') if v.strip()]
    return [v for v in (v.strip() for v in vals) if v]

def _parse_dt(s):
    if not s: return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try: return datetime.strptime(s, fmt)
        except Exception: pass
    return None

# ---- A1: GET /ext/contacts ----
@bp.get("/contacts")
def list_contacts():
    try:
        page = max(int(request.args.get("page", 1)), 1)
        size = min(max(int(request.args.get("size", 20)), 1), 200)
    except Exception:
        return _err("VALIDATION_ERROR", "page/size must be numbers")

    q = (request.args.get("q") or "").strip()
    tag_ids = _parse_list(request.args, "tag_ids")
    owner_userids = _parse_list(request.args, "owner_userids")
    has_unionid = request.args.get("has_unionid", "").strip()
    created_from = _parse_dt(request.args.get("created_from"))
    created_to   = _parse_dt(request.args.get("created_to"))
    touched_from = _parse_dt(request.args.get("touched_from"))
    touched_to   = _parse_dt(request.args.get("touched_to"))

    where, params, join_tag = ["1=1"], [], ""
    if q:
        like = f"%{q}%"
        where.append("(ec.name LIKE %s OR ec.corp_name LIKE %s OR ec.corp_full_name LIKE %s)")
        params += [like, like, like]
    if owner_userids:
        where.append("ec.follow_userid IN (" + ",".join(["%s"]*len(owner_userids)) + ")")
        params += owner_userids
    if has_unionid in ("0","1",0,1):
        if str(has_unionid)=="1":
            where.append("(ec.unionid IS NOT NULL AND ec.unionid<>'')")
        else:
            where.append("(ec.unionid IS NULL OR ec.unionid='')")
    if created_from:
        where.append("ec.created_at >= %s"); params.append(created_from)
    if created_to:
        where.append("ec.created_at <= %s"); params.append(created_to)
    if touched_from:
        where.append("ec.updated_at >= %s"); params.append(touched_from)
    if touched_to:
        where.append("ec.updated_at <= %s"); params.append(touched_to)
    if tag_ids:
        join_tag = "JOIN ext_contact_tag ect ON ect.external_userid=ec.external_userid"
        where.append("ect.tag_id IN (" + ",".join(["%s"]*len(tag_ids)) + ")")
        params += tag_ids

    offset = (page-1)*size
    conn = get_mysql_conn()
    with conn.cursor() as cur:
        # total
        cur.execute(f"""
          SELECT COUNT(DISTINCT ec.external_userid) AS total
          FROM ext_contact ec
          {join_tag}
          WHERE {' AND '.join(where)}
        """, params)
        total = int(cur.fetchone()["total"])

        # items
        cur.execute(f"""
          SELECT
            ec.external_userid, ec.name, ec.corp_name, ec.corp_full_name,
            ec.follow_userid AS owner_userid, ec.unionid, ec.avatar,
            ec.created_at, ec.updated_at
          FROM ext_contact ec
          {join_tag}
          WHERE {' AND '.join(where)}
          GROUP BY ec.external_userid
          ORDER BY ec.updated_at DESC, ec.external_userid
          LIMIT %s OFFSET %s
        """, params + [size, offset])
        rows = cur.fetchall()

        # tags（按页聚合，避免全量 group_concat 过大）
        eids = [r["external_userid"] for r in rows]
        tag_map = {}
        if eids:
            cur.execute(f"""
              SELECT external_userid, GROUP_CONCAT(tag_id ORDER BY tag_id) AS tag_ids
              FROM ext_contact_tag
              WHERE external_userid IN ({','.join(['%s']*len(eids))})
              GROUP BY external_userid
            """, eids)
            for r in cur.fetchall():
                tag_map[r["external_userid"]] = (r["tag_ids"] or "").split(",") if r.get("tag_ids") else []

    items = []
    for r in rows:
        items.append({
            "external_userid": r["external_userid"],
            "name": r.get("name"),
            "corp_name": r.get("corp_name") or r.get("corp_full_name"),
            "owner_userid": r.get("owner_userid"),
            "unionid": r.get("unionid"),
            "avatar": r.get("avatar"),
            # 目前仅有 tag_id，没有标签名表，先返回 id 列表；后续可接入标签字典表映射为名字
            "tags": tag_map.get(r["external_userid"], []),
            "created_at": str(r.get("created_at") or ""),
            "updated_at": str(r.get("updated_at") or "")
        })

    return _ok({"items": items, "total": total, "page": page, "size": size})

# ---- A2: GET /ext/tags （按 tag_id 汇总）----
@bp.get("/tags")
def list_tags():
    try:
        page = max(int(request.args.get("page", 1)), 1)
        size = min(max(int(request.args.get("size", 20)), 1), 200)
    except Exception:
        return _err("VALIDATION_ERROR", "page/size must be numbers")
    offset = (page-1)*size

    conn = get_mysql_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(1) AS total FROM (SELECT 1 FROM ext_contact_tag GROUP BY tag_id) t")
        total = int(cur.fetchone()["total"])
        cur.execute("""
          SELECT tag_id, COUNT(DISTINCT external_userid) AS members
          FROM ext_contact_tag
          GROUP BY tag_id
          ORDER BY members DESC, tag_id
          LIMIT %s OFFSET %s
        """, [size, offset])
        rows = cur.fetchall()

    items = [{"tag_id": r["tag_id"], "members": int(r["members"])} for r in rows]
    return _ok({"items": items, "total": total, "page": page, "size": size})
