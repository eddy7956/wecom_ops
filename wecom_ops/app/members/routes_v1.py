# /www/wwwroot/wecom_ops/app/members/routes_v1.py
from flask import Blueprint, request, jsonify, g
from app.core.db import get_mysql_conn

bp = Blueprint("members_v1", __name__, url_prefix="/api/v1/members")

# ---------- helpers ----------
def _ok(data, status=200):
    resp = jsonify({"ok": True, "data": data})
    resp.headers["X-Request-Id"] = getattr(g, "trace_id", "")
    return resp, status

def _err(message, detail="", code="INTERNAL_ERROR", status=500):
    resp = jsonify({"ok": False, "error": {"code": code, "message": str(message), "detail": str(detail)}})
    resp.headers["X-Request-Id"] = getattr(g, "trace_id", "")
    return resp, status

def _get_int(name, default):
    raw = request.args.get(name, str(default))
    try:
        val = int(str(raw))
    except Exception:
        val = default
    if name == "page":
        return max(1, val)
    if name == "size":
        return max(1, min(200, val))
    return val

def _csv(name):
    raw = request.args.get(name, "")
    vals = []
    for p in str(raw).split(","):
        p = p.strip()
        if p:
            vals.append(p)
    return vals

def _first_val(row, default=0):
    if row is None:
        return default
    if isinstance(row, dict):
        for v in row.values():
            return v
        return default
    return row[0] if len(row) > 0 else default

def _get(row, key, idx):
    if isinstance(row, dict):
        return row.get(key)
    return row[idx]

def _split_csv_or_empty(s):
    if not s:
        return []
    return [x for x in str(s).split(",") if x]

def _get_flag(name):
    """解析布尔筛选：返回 None / 0 / 1"""
    v = request.args.get(name)
    if v is None:
        return None
    vs = str(v).strip().lower()
    if vs in ("1", "true", "t", "yes", "y"):
        return 1
    if vs in ("0", "false", "f", "no", "n"):
        return 0
    return None

# ---------- /members/meta ----------
@bp.get("/meta")
def meta():
    """
    元数据（分页）：
      - only=tags|owners|stores（可逗号分隔；省略=全部）
      - q=模糊关键词
      - page,size 分页
      - unassigned=1|0  是否只看待分配/排除待分配
    说明：
      * 仅统计 is_deleted=0。
      * 不做手机号规范化。
    """
    conn = None
    cur = None
    try:
        only_raw = (request.args.get("only") or "").strip()
        only_set = set([s.strip().lower() for s in only_raw.split(",") if s.strip()]) if only_raw else set()
        page = _get_int("page", 1)
        size = _get_int("size", 50)
        offset = (page - 1) * size
        q = (request.args.get("q") or "").strip()
        qlike = f"%{q}%" if q else None
        unassigned = _get_flag("unassigned")

        out = {}
        conn = get_mysql_conn()
        cur = conn.cursor()

        # 1) tags
        if not only_set or "tags" in only_set:
            params, where = [], ["COALESCE(e.is_deleted,0)=0"]
            if unassigned is not None:
                where.append("COALESCE(e.is_unassigned,0)=%s")
                params.append(int(unassigned))
            if q:
                where.append("(t.tag_name LIKE %s OR t.group_name LIKE %s)")
                params += [qlike, qlike]

            cur.execute(f"""
              SELECT COUNT(*) FROM (
                SELECT t.tag_id
                FROM wecom_ops.ext_contact_tag t
                JOIN wecom_ops.ext_contact e ON e.external_userid=t.external_userid
                WHERE {" AND ".join(where)}
                GROUP BY t.tag_id
              ) x
            """, params)
            total = int(_first_val(cur.fetchone(), 0))

            cur.execute(f"""
              SELECT
                  t.tag_id,
                  COALESCE(t.tag_name, t.tag_id) AS tag_name,
                  t.group_name,
                  COUNT(DISTINCT t.external_userid) AS members
              FROM wecom_ops.ext_contact_tag t
              JOIN wecom_ops.ext_contact e ON e.external_userid=t.external_userid
              WHERE {" AND ".join(where)}
              GROUP BY t.tag_id, COALESCE(t.tag_name, t.tag_id), t.group_name
              ORDER BY members DESC, tag_name ASC
              LIMIT %s OFFSET %s
            """, params + [size, offset])
            rows = cur.fetchall()
            out["tags"] = {
                "items": [{
                    "tag_id":    _get(r, "tag_id", 0),
                    "tag_name":  _get(r, "tag_name", 1),
                    "group_name":_get(r, "group_name", 2),
                    "members":   int(_get(r, "members", 3)),
                } for r in rows],
                "page": page, "size": size, "total": total
            }

        # 2) owners
        if not only_set or "owners" in only_set:
            params, where = [], ["v.is_deleted=0"]
            if q:
                where.append("(v.primary_owner_name LIKE %s OR v.primary_owner_userid LIKE %s)")
                params += [qlike, qlike]
            # 为支持 unassigned 过滤，连接 ext_contact
            if unassigned is not None:
                where.append("COALESCE(e.is_unassigned,0)=%s")
                params.append(int(unassigned))

            cur.execute(f"""
              SELECT COUNT(*) FROM (
                SELECT v.primary_owner_userid, v.primary_owner_name
                FROM wecom_ops.vw_mobile_to_external v
                JOIN wecom_ops.ext_contact e ON e.external_userid=v.external_userid
                WHERE {" AND ".join(where)}
                GROUP BY v.primary_owner_userid, v.primary_owner_name
              ) x
            """, params)
            total = int(_first_val(cur.fetchone(), 0))

            cur.execute(f"""
              SELECT v.primary_owner_userid AS userid,
                     v.primary_owner_name   AS name,
                     COUNT(*)               AS members
              FROM wecom_ops.vw_mobile_to_external v
              JOIN wecom_ops.ext_contact e ON e.external_userid=v.external_userid
              WHERE {" AND ".join(where)}
              GROUP BY v.primary_owner_userid, v.primary_owner_name
              ORDER BY members DESC, name ASC
              LIMIT %s OFFSET %s
            """, params + [size, offset])
            rows = cur.fetchall()
            out["owners"] = {
                "items": [{
                    "userid":  _get(r, "userid", 0),
                    "name":    _get(r, "name", 1),
                    "members": int(_get(r, "members", 2)),
                } for r in rows],
                "page": page, "size": size, "total": total
            }

        # 3) stores/brands
        if not only_set or "stores" in only_set:
            params, where = [], ["v.is_deleted=0"]
            if q:
                where.append("(v.store_name LIKE %s OR v.department_brand LIKE %s OR v.store_code LIKE %s)")
                params += [qlike, qlike, qlike]
            if unassigned is not None:
                where.append("COALESCE(e.is_unassigned,0)=%s")
                params.append(int(unassigned))

            cur.execute(f"""
              SELECT COUNT(*) FROM (
                SELECT v.store_code, v.store_name, v.department_brand
                FROM wecom_ops.vw_mobile_to_external v
                JOIN wecom_ops.ext_contact e ON e.external_userid=v.external_userid
                WHERE {" AND ".join(where)}
                GROUP BY v.store_code, v.store_name, v.department_brand
              ) x
            """, params)
            total = int(_first_val(cur.fetchone(), 0))

            cur.execute(f"""
              SELECT v.store_code, v.store_name, v.department_brand, COUNT(*) AS members
              FROM wecom_ops.vw_mobile_to_external v
              JOIN wecom_ops.ext_contact e ON e.external_userid=v.external_userid
              WHERE {" AND ".join(where)}
              GROUP BY v.store_code, v.store_name, v.department_brand
              ORDER BY members DESC, COALESCE(v.store_name,''), COALESCE(v.department_brand,'')
              LIMIT %s OFFSET %s
            """, params + [size, offset])
            rows = cur.fetchall()
            out["stores"] = {
                "items": [{
                    "store_code":       _get(r, "store_code", 0),
                    "store_name":       _get(r, "store_name", 1),
                    "department_brand": _get(r, "department_brand", 2),
                    "members":          int(_get(r, "members", 3)),
                } for r in rows],
                "page": page, "size": size, "total": total
            }

        return _ok(out)
    except Exception as e:
        return _err(message=e, detail="")
    finally:
        try:
            cur and cur.close()
        except Exception:
            pass
        try:
            conn and conn.close()
        except Exception:
            pass

# ---------- 统一的过滤构建 ----------
def _build_filters():
    where = ["v.is_deleted=0"]
    params = []

    # q: 模糊检索（姓名/跟进人/门店/品牌/手机号）
    q = (request.args.get("q") or "").strip()
    if q:
        like = f"%{q}%"
        where.append("(e.name LIKE %s OR v.primary_owner_name LIKE %s OR v.store_name LIKE %s OR v.department_brand LIKE %s OR v.mobile_raw LIKE %s)")
        params += [like, like, like, like, like]

    # 指定 owner
    owner_userids = _csv("owner_userids")
    if owner_userids:
        where.append("v.primary_owner_userid IN (%s)" % ",".join(["%s"] * len(owner_userids)))
        params += owner_userids

    # 指定 store_code
    store_codes = _csv("store_codes")
    if store_codes:
        where.append("v.store_code IN (%s)" % ",".join(["%s"] * len(store_codes)))
        params += store_codes

    # 指定 brand
    brands = _csv("brands")
    if brands:
        where.append("v.department_brand IN (%s)" % ",".join(["%s"] * len(brands)))
        params += brands

    # 指定 tag_ids（用 EXISTS 过滤）
    tag_ids = _csv("tag_ids")
    if tag_ids:
        where.append("""
          EXISTS (
            SELECT 1 FROM wecom_ops.ext_contact_tag t
            WHERE t.external_userid = v.external_userid
              AND t.tag_id IN (%s)
          )
        """ % ",".join(["%s"] * len(tag_ids)))
        params += tag_ids

    # 是否待分配（依赖 ext_contact.is_unassigned）
    unassigned = _get_flag("unassigned")
    if unassigned is not None:
        where.append("COALESCE(e.is_unassigned,0)=%s")
        params.append(int(unassigned))

    return where, params

# ---------- /members/list ----------
@bp.get("/list")
def list_members():
    """
    列表：
      - 支持 q / owner_userids / store_codes / brands / tag_ids / unassigned 过滤
      - 分页 page,size
    返回字段：
      external_userid, unionid, crm_user_id, vip_name, mobile (raw),
      store_code, store_name, department_brand,
      owner_userid/name, tags[], is_unassigned, is_deleted,
      ext 基本信息(name, avatar, corp_name), created_at/updated_at
    """
    conn = None
    cur = None
    try:
        page = _get_int("page", 1)
        size = _get_int("size", 20)
        offset = (page - 1) * size

        where, params = _build_filters()

        conn = get_mysql_conn()
        cur = conn.cursor()

        # total
        cur.execute(f"""
          SELECT COUNT(*)
          FROM wecom_ops.vw_mobile_to_external v
          JOIN wecom_ops.ext_contact e ON e.external_userid = v.external_userid
          WHERE {" AND ".join(where)}
        """, params)
        total = int(_first_val(cur.fetchone(), 0))

        # page
        cur.execute(f"""
          SELECT
              v.external_userid, v.unionid,
              v.crm_user_id, v.vip_name, v.mobile_raw,
              v.store_code, v.store_name, v.department_brand,
              v.primary_owner_userid, v.primary_owner_name,
              v.tag_names,
              COALESCE(e.is_unassigned,0) AS is_unassigned,
              COALESCE(e.is_deleted,0)    AS is_deleted,
              e.name AS ext_name, e.avatar, e.corp_name,
              e.created_at, e.updated_at
          FROM wecom_ops.vw_mobile_to_external v
          JOIN wecom_ops.ext_contact e ON e.external_userid = v.external_userid
          WHERE {" AND ".join(where)}
          ORDER BY e.updated_at DESC
          LIMIT %s OFFSET %s
        """, params + [size, offset])
        rows = cur.fetchall()

        items = []
        for r in rows:
            tag_names = _get(r, "tag_names", 10)
            items.append({
                "external_userid": _get(r, "external_userid", 0),
                "unionid":         _get(r, "unionid", 1),
                "crm_user_id":     _get(r, "crm_user_id", 2),
                "vip_name":        _get(r, "vip_name", 3),
                "mobile":          _get(r, "mobile_raw", 4),
                "store_code":      _get(r, "store_code", 5),
                "store_name":      _get(r, "store_name", 6),
                "department_brand":_get(r, "department_brand", 7),
                "owner_userid":    _get(r, "primary_owner_userid", 8),
                "owner_name":      _get(r, "primary_owner_name", 9),
                "tags":            _split_csv_or_empty(tag_names),
                "is_unassigned":   int(_get(r, "is_unassigned", 11) or 0),
                "is_deleted":      int(_get(r, "is_deleted", 12) or 0),
                "name":            _get(r, "ext_name", 13),
                "avatar":          _get(r, "avatar", 14),
                "corp_name":       _get(r, "corp_name", 15),
                "created_at":      _get(r, "created_at", 16),
                "updated_at":      _get(r, "updated_at", 17),
            })

        return _ok({"items": items, "page": page, "size": size, "total": total})
    except Exception as e:
        return _err(message=e, detail="")
    finally:
        try:
            cur and cur.close()
        except Exception:
            pass
        try:
            conn and conn.close()
        except Exception:
            pass

# ---------- /members/estimate ----------
@bp.get("/estimate")
def estimate_members():
    """返回当前过滤条件下的总数（不分页）。"""
    conn = None
    cur = None
    try:
        where, params = _build_filters()
        conn = get_mysql_conn()
        cur = conn.cursor()
        cur.execute(f"""
          SELECT COUNT(*)
          FROM wecom_ops.vw_mobile_to_external v
          JOIN wecom_ops.ext_contact e ON e.external_userid = v.external_userid
          WHERE {" AND ".join(where)}
        """, params)
        total = int(_first_val(cur.fetchone(), 0))
        return _ok({"total": total})
    except Exception as e:
        return _err(message=e, detail="")
    finally:
        try:
            cur and cur.close()
        except Exception:
            pass
        try:
            conn and conn.close()
        except Exception:
            pass

# ---------- /members/detail ----------
@bp.get("/detail")
def detail_member():
    """
    详情：
      - external_userid=...
    返回字段：
      基本同 list 的一条 + tags 结构化 + ext_detail(detail_json 原样)
    """
    conn = None
    cur = None
    try:
        external_userid = (request.args.get("external_userid") or "").strip()
        if not external_userid:
            return _err("missing external_userid", code="BAD_REQUEST", status=400)

        conn = get_mysql_conn()
        cur = conn.cursor()

        # 主体信息（v + e）
        cur.execute("""
          SELECT
              v.external_userid, v.unionid,
              v.crm_user_id, v.vip_name, v.mobile_raw,
              v.store_code, v.store_name, v.department_brand,
              v.primary_owner_userid, v.primary_owner_name,
              COALESCE(e.is_unassigned,0) AS is_unassigned,
              COALESCE(e.is_deleted,0)    AS is_deleted,
              e.name AS ext_name, e.avatar, e.corp_name,
              e.created_at, e.updated_at, e.detail_json
          FROM wecom_ops.vw_mobile_to_external v
          JOIN wecom_ops.ext_contact e ON e.external_userid = v.external_userid
          WHERE v.external_userid = %s
          LIMIT 1
        """, [external_userid])
        row = cur.fetchone()
        if not row:
            return _err("member not found", code="NOT_FOUND", status=404)

        # 标签结构化
        cur.execute("""
          SELECT tag_id, COALESCE(tag_name, tag_id) AS tag_name, group_name
          FROM wecom_ops.ext_contact_tag
          WHERE external_userid = %s
        """, [external_userid])
        tag_rows = cur.fetchall()
        tags = [{
            "tag_id":   _get(tr, "tag_id", 0),
            "tag_name": _get(tr, "tag_name", 1),
            "group_name": _get(tr, "group_name", 2),
        } for tr in tag_rows]

        data = {
            "external_userid": _get(row, "external_userid", 0),
            "unionid":         _get(row, "unionid", 1),
            "crm_user_id":     _get(row, "crm_user_id", 2),
            "vip_name":        _get(row, "vip_name", 3),
            "mobile":          _get(row, "mobile_raw", 4),
            "store_code":      _get(row, "store_code", 5),
            "store_name":      _get(row, "store_name", 6),
            "department_brand":_get(row, "department_brand", 7),
            "owner_userid":    _get(row, "primary_owner_userid", 8),
            "owner_name":      _get(row, "primary_owner_name", 9),
            "is_unassigned":   int(_get(row, "is_unassigned", 10) or 0),
            "is_deleted":      int(_get(row, "is_deleted", 11) or 0),
            "name":            _get(row, "ext_name", 12),
            "avatar":          _get(row, "avatar", 13),
            "corp_name":       _get(row, "corp_name", 14),
            "created_at":      _get(row, "created_at", 15),
            "updated_at":      _get(row, "updated_at", 16),
            "ext_detail":      _get(row, "detail_json", 17),
            "tags":            tags,
        }
        return _ok(data)
    except Exception as e:
        return _err(message=e, detail="")
    finally:
        try:
            cur and cur.close()
        except Exception:
            pass
        try:
            conn and conn.close()
        except Exception:
            pass
