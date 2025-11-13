from flask import Blueprint, request, jsonify, g
from app.core.db import get_mysql_conn

bp = Blueprint("org_v1", __name__, url_prefix="/api/v1/org")

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

def _table_exists(conn, table_name: str) -> bool:
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DATABASE() AS db")
            db = cur.fetchone()["db"]
            cur.execute("""
              SELECT 1 FROM information_schema.tables
              WHERE table_schema=%s AND table_name=%s
              LIMIT 1
            """, [db, table_name])
            return cur.fetchone() is not None
    except Exception:
        return False

@bp.get("/employees")
def list_employees():
    # 支持分页
    try:
        page = max(int(request.args.get("page", 1)), 1)
        size = min(max(int(request.args.get("size", 20)), 1), 200)
    except Exception:
        return _err("VALIDATION_ERROR", "page/size must be numbers")
    offset = (page-1)*size

    conn = get_mysql_conn()
    items, total = [], 0

    # 1) 优先从 ext_follow_user 聚合（更准）
    try:
        if _table_exists(conn, "ext_follow_user"):
            with conn.cursor() as cur:
                cur.execute("""
                  SELECT COUNT(1) AS total
                  FROM (SELECT 1
                        FROM ext_follow_user
                        WHERE userid IS NOT NULL AND userid<>''
                        GROUP BY userid) t
                """)
                total = int(cur.fetchone()["total"])
                cur.execute("""
                  SELECT userid, COUNT(DISTINCT external_userid) AS members
                  FROM ext_follow_user
                  WHERE userid IS NOT NULL AND userid<>''
                  GROUP BY userid
                  ORDER BY members DESC, userid
                  LIMIT %s OFFSET %s
                """, [size, offset])
                rows = cur.fetchall()
                items = [{"userid": r["userid"], "name": r["userid"], "members": int(r["members"])} for r in rows]
    except Exception:
        # 出错则回退到 ext_contact 聚合
        items, total = [], 0

    # 2) 回退 ext_contact.follow_userid（当 ext_follow_user 不存在或无数据）
    if total == 0:
        with conn.cursor() as cur:
            cur.execute("""
              SELECT COUNT(1) AS total FROM
              (SELECT 1
               FROM ext_contact
               WHERE follow_userid IS NOT NULL AND follow_userid<>''
               GROUP BY follow_userid) t
            """)
            total = int(cur.fetchone()["total"])
            if total > 0:
                cur.execute("""
                  SELECT follow_userid AS userid, COUNT(DISTINCT external_userid) AS members
                  FROM ext_contact
                  WHERE follow_userid IS NOT NULL AND follow_userid<>''
                  GROUP BY follow_userid
                  ORDER BY members DESC, userid
                  LIMIT %s OFFSET %s
                """, [size, offset])
                rows = cur.fetchall()
                items = [{"userid": r["userid"], "name": r["userid"], "members": int(r["members"])} for r in rows]

    return _ok({"items": items, "total": total, "page": page, "size": size})
