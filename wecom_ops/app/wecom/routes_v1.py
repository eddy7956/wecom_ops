# app/wecom/routes_v1.py
from __future__ import annotations

import json
import re
import time
import traceback
from typing import Any, Iterable, List, Tuple

from flask import Blueprint, request, jsonify, g

from app.core.db import get_mysql_conn

bp = Blueprint("wecom_v1", __name__, url_prefix="/api/v1/wecom")


# -------------------------
# utils
# -------------------------
def _ok(data: Any, code: int = 200):
    resp = jsonify({"ok": True, "data": data})
    resp.headers["X-Request-Id"] = getattr(g, "trace_id", "")
    return resp, code


def _bad(msg: str, code: int = 400, detail: str = ""):
    resp = jsonify({"ok": False, "error": {"code": "BAD_REQUEST", "message": msg, "detail": detail}})
    resp.headers["X-Request-Id"] = getattr(g, "trace_id", "")
    return resp, code


def _err(msg: str, code: int = 500, detail: str = ""):
    resp = jsonify({"ok": False, "error": {"code": "INTERNAL_ERROR", "message": msg, "detail": detail}})
    resp.headers["X-Request-Id"] = getattr(g, "trace_id", "")
    return resp, code


def _parse_int(val: Any, default: int, min_v: int | None = None, max_v: int | None = None) -> int:
    try:
        iv = int(val)
    except Exception:
        iv = default
    if min_v is not None and iv < min_v:
        iv = min_v
    if max_v is not None and iv > max_v:
        iv = max_v
    return iv


def _rows_to_dicts(cur, rows: Iterable[Tuple]) -> List[dict]:
    """兼容 tuple/dict 两种游标结果"""
    rows = list(rows or [])
    if not rows:
        return []
    first = rows[0]
    if isinstance(first, dict):
        # 字典游标直接复制一份，避免外部改动引用
        return [dict(r) for r in rows]
    # 元组游标按列描述拼装
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in rows]


def _ex_text(e: Exception, sql: str = "") -> str:
    etype = e.__class__.__name__
    errno = getattr(e, "errno", None)
    sqlstate = getattr(e, "sqlstate", None)
    msg = getattr(e, "msg", None)
    args = getattr(e, "args", None)

    parts = [f"type={etype}"]
    if errno is not None:
        parts.append(f"errno={errno}")
    if sqlstate:
        parts.append(f"sqlstate={sqlstate}")
    if msg not in (None, ""):
        parts.append(f"msg={msg}")
    if args:
        parts.append(f"args={repr(args)[:300]}")
    base = " | ".join(parts)
    if sql:
        slim = re.sub(r"\s+", " ", sql).strip()
        if len(slim) > 480:
            slim = slim[:240] + " ... " + slim[-200:]
        base += f" | sql={slim}"
    return base


def _exec(cur, sql: str, params: Tuple | List | None = None):
    try:
        cur.execute(sql, params or ())
    except Exception as e:
        raise RuntimeError(_ex_text(e, sql))


def _fetch_all_dicts(cur, sql: str, params: Tuple | List | None = None) -> List[dict]:
    _exec(cur, sql, params)
    return _rows_to_dicts(cur, cur.fetchall())


def _fetch_one_value(cur, sql: str, params: Tuple | List | None = None, default: Any = None):
    """兼容 tuple/dict 行；优先取 total/count 键；否则取首列/首值"""
    _exec(cur, sql, params)
    r = cur.fetchone()
    if r is None:
        return default
    try:
        if isinstance(r, dict):
            for k in ("total", "count", "TOTAL", "COUNT"):
                if k in r:
                    return r[k]
            # 字典游标：取第一个值
            return next(iter(r.values()))
        # 元组/列表：首列
        return r[0]
    except Exception:
        return default


# -------------------------
# 回调入口（GET=403；POST 支持 Debug 直通）
# -------------------------
@bp.get("/callback")
def wecom_verify():
    return _err("forbidden", 403)


@bp.post("/callback")
def wecom_callback():
    debug = request.headers.get("X-Wecom-Debug") == "1"
    try:
        payload = request.get_json(force=True, silent=False) or {}
    except Exception as e:
        return _bad("invalid json", 400, str(e))

    event = (payload.get("Event") or "").strip()
    ext_id = (payload.get("ExternalUserID") or "").strip()
    detail = payload.get("Detail")
    from_user = (payload.get("FromUserName") or "").strip()
    create_ts = _parse_int(payload.get("CreateTime"), int(time.time()))

    if not event or not ext_id:
        return _bad("missing Event or ExternalUserID", 400)

    try:
        with get_mysql_conn() as conn:
            cur = conn.cursor()

            # 基础存在性
            _exec(
                cur,
                """
                INSERT INTO wecom_ops.ext_contact (external_userid, is_deleted, updated_at)
                VALUES (%s, 0, NOW())
                ON DUPLICATE KEY UPDATE updated_at=NOW()
                """,
                (ext_id,),
            )

            if event in ("add_external_contact", "edit_external_contact"):
                _exec(
                    cur,
                    """
                    UPDATE wecom_ops.ext_contact
                       SET is_deleted=0,
                           is_unassigned=0,
                           updated_at=NOW()
                     WHERE external_userid=%s
                    """,
                    (ext_id,),
                )
                if from_user:
                    _exec(
                        cur,
                        "INSERT IGNORE INTO wecom_ops.ext_contact_follow (external_userid, userid) VALUES (%s, %s)",
                        (ext_id, from_user),
                    )
                if detail is not None:
                    try:
                        dj = json.dumps(detail, ensure_ascii=False)
                        _exec(
                            cur,
                            "UPDATE wecom_ops.ext_contact SET detail_json=%s, updated_at=NOW() WHERE external_userid=%s",
                            (dj, ext_id),
                        )
                    except Exception:
                        pass
                _exec(
                    cur,
                    """
                    UPDATE wecom_ops.ext_unassigned
                       SET is_active=0,
                           handover_userid=COALESCE(%s, handover_userid),
                           updated_at=NOW()
                     WHERE external_userid=%s
                    """,
                    (from_user or None, ext_id),
                )

            elif event == "del_external_contact":
                if from_user:
                    _exec(
                        cur,
                        "DELETE FROM wecom_ops.ext_contact_follow WHERE external_userid=%s AND userid=%s",
                        (ext_id, from_user),
                    )
                left = _fetch_one_value(
                    cur,
                    "SELECT COUNT(*) AS total FROM wecom_ops.ext_contact_follow WHERE external_userid=%s",
                    (ext_id,),
                    0,
                )
                if left and int(left) > 0:
                    _exec(cur, "UPDATE wecom_ops.ext_contact SET updated_at=NOW() WHERE external_userid=%s", (ext_id,))
                else:
                    _exec(
                        cur,
                        "UPDATE wecom_ops.ext_contact SET is_unassigned=1, updated_at=NOW() WHERE external_userid=%s",
                        (ext_id,),
                    )
                    _exec(
                        cur,
                        """
                        INSERT INTO wecom_ops.ext_unassigned (external_userid, is_active, reason, created_at, updated_at)
                        VALUES (%s, 1, %s, NOW(), NOW())
                        ON DUPLICATE KEY UPDATE
                          is_active=VALUES(is_active),
                          reason=VALUES(reason),
                          updated_at=VALUES(updated_at)
                        """,
                        (ext_id, "del_external_contact"),
                    )

            elif event == "transfer_fail":
                _exec(
                    cur,
                    "UPDATE wecom_ops.ext_contact SET is_unassigned=1, updated_at=NOW() WHERE external_userid=%s",
                    (ext_id,),
                )
                _exec(
                    cur,
                    """
                    INSERT INTO wecom_ops.ext_unassigned (external_userid, is_active, reason, created_at, updated_at)
                    VALUES (%s, 1, %s, NOW(), NOW())
                    ON DUPLICATE KEY UPDATE
                      is_active=VALUES(is_active),
                      reason=VALUES(reason),
                      updated_at=VALUES(updated_at)
                    """,
                    (ext_id, "transfer_fail"),
                )

            elif event == "change_external_tag":
                add = (detail or {}).get("add") or []
                rmv = (detail or {}).get("remove") or []
                add = [t for t in add if t]
                rmv = [t for t in rmv if t]
                if add:
                    cur.executemany(
                        "INSERT IGNORE INTO wecom_ops.ext_contact_tag (external_userid, tag_id) VALUES (%s, %s)",
                        [(ext_id, t) for t in add],
                    )
                if rmv:
                    placeholders = ",".join(["%s"] * len(rmv))
                    _exec(
                        cur,
                        f"DELETE FROM wecom_ops.ext_contact_tag WHERE external_userid=%s AND tag_id IN ({placeholders})",
                        (ext_id, *rmv),
                    )
                _exec(cur, "UPDATE wecom_ops.ext_contact SET updated_at=NOW() WHERE external_userid=%s", (ext_id,))

            else:
                pass

            conn.commit()
        return _ok({"event": event, "external_userid": ext_id, "debug": debug})
    except Exception as e:
        return _err(_ex_text(e), 500, traceback.format_exc())


# -------------------------
# 待分配池：估算 / 列表 / 分配
# -------------------------
def _build_where_for_unassigned(filters: dict | None) -> Tuple[str, List[Any], bool]:
    """
    返回: where_sql, args, need_view
    当存在 brands/stores/q 时需要关联视图（need_view=True）
    """
    where = ["un.is_active=1", "COALESCE(e.is_deleted,0)=0"]
    args: List[Any] = []

    brands = (filters or {}).get("brands") or []
    stores = (filters or {}).get("stores") or []
    kw = ((filters or {}).get("q") or "").strip()

    need_view = bool(brands or stores or kw)

    if brands:
        where.append("v.department_brand IN (" + ",".join(["%s"] * len(brands)) + ")")
        args.extend(brands)

    if stores:
        where.append("v.store_name IN (" + ",".join(["%s"] * len(stores)) + ")")
        args.extend(stores)

    if kw:
        like = f"%{kw}%"
        where.append(
            "("
            "v.tag_names LIKE %s OR v.store_name LIKE %s OR v.department_brand LIKE %s OR "
            "v.vip_name LIKE %s OR v.mobile_raw LIKE %s"
            ")"
        )
        args.extend([like, like, like, like, like])

    return " AND ".join(where), args, need_view


@bp.post("/unassigned/estimate")
def unassigned_estimate():
    """
    body: {"filters": {"brands":["Nike"], "stores":["万象城"], "q":"跑步"}, "limit":0}
    无筛选时会尝试不关联视图，从而避免视图临时不可用导致 500。
    """
    try:
        body = request.get_json(force=True, silent=True) or {}
        filters = body.get("filters") or {}
        where_sql, args, need_view = _build_where_for_unassigned(filters)

        with get_mysql_conn() as conn:
            cur = conn.cursor()

            if not need_view:
                sql = f"""
                    SELECT COUNT(1) AS total
                      FROM wecom_ops.ext_unassigned un
                      JOIN wecom_ops.ext_contact e
                        ON e.external_userid = un.external_userid
                     WHERE {where_sql}
                """
                total = _fetch_one_value(cur, sql, args, 0)
                return _ok({"total": int(total or 0)})

            sql = f"""
                SELECT COUNT(1) AS total
                  FROM wecom_ops.ext_unassigned un
                  JOIN wecom_ops.ext_contact e
                    ON e.external_userid = un.external_userid
             LEFT JOIN wecom_ops.vw_mobile_to_external v
                    ON v.external_userid = un.external_userid
                 WHERE {where_sql}
            """
            total = _fetch_one_value(cur, sql, args, 0)
            return _ok({"total": int(total or 0)})

    except Exception as e:
        return _err(_ex_text(e), 500, traceback.format_exc())


@bp.get("/unassigned/list")
def unassigned_list():
    """
    query: page/size, q / brands / stores
    - 有筛选或需要丰富字段 => 关联视图
    - 视图不可用时自动降级（仅返回基本字段）
    """
    try:
        page = _parse_int(request.args.get("page"), 1, 1)
        size = _parse_int(request.args.get("size"), 20, 1, 200)

        def _split_param(name: str) -> List[str]:
            vals = request.args.getlist(name)
            parts: List[str] = []
            for seg in vals:
                parts.extend([x for x in re.split(r"[,\s]+", (seg or "").strip()) if x])
            return parts

        filters = {
            "q": (request.args.get("q") or "").strip(),
            "brands": _split_param("brands"),
            "stores": _split_param("stores"),
        }
        where_sql, args, need_view = _build_where_for_unassigned(filters)
        offset = (page - 1) * size

        with get_mysql_conn() as conn:
            cur = conn.cursor()

            # total
            if not need_view:
                sql_total = f"""
                    SELECT COUNT(1) AS total
                      FROM wecom_ops.ext_unassigned un
                      JOIN wecom_ops.ext_contact e
                        ON e.external_userid = un.external_userid
                     WHERE {where_sql}
                """
                total = _fetch_one_value(cur, sql_total, args, 0)
            else:
                sql_total = f"""
                    SELECT COUNT(1) AS total
                      FROM wecom_ops.ext_unassigned un
                      JOIN wecom_ops.ext_contact e
                        ON e.external_userid = un.external_userid
                 LEFT JOIN wecom_ops.vw_mobile_to_external v
                        ON v.external_userid = un.external_userid
                     WHERE {where_sql}
                """
                total = _fetch_one_value(cur, sql_total, args, 0)

            # list（优先视图，失败降级）
            degraded = False
            try:
                sql_list = f"""
                    SELECT
                        un.external_userid,
                        un.reason,
                        un.handover_userid,
                        un.created_at,
                        un.updated_at,
                        v.vip_name,
                        v.mobile_raw,
                        v.store_name,
                        v.department_brand,
                        v.tag_names
                      FROM wecom_ops.ext_unassigned un
                      JOIN wecom_ops.ext_contact e
                        ON e.external_userid = un.external_userid
                 LEFT JOIN wecom_ops.vw_mobile_to_external v
                        ON v.external_userid = un.external_userid
                     WHERE {where_sql}
                  ORDER BY un.updated_at DESC
                     LIMIT %s OFFSET %s
                """
                rows = _fetch_all_dicts(cur, sql_list, args + [size, offset])
            except Exception as e1:
                degraded = True
                sql_list2 = f"""
                    SELECT
                        un.external_userid,
                        un.reason,
                        un.handover_userid,
                        un.created_at,
                        un.updated_at
                      FROM wecom_ops.ext_unassigned un
                      JOIN wecom_ops.ext_contact e
                        ON e.external_userid = un.external_userid
                     WHERE {where_sql}
                  ORDER BY un.updated_at DESC
                     LIMIT %s OFFSET %s
                """
                try:
                    base_rows = _fetch_all_dicts(cur, sql_list2, args + [size, offset])
                    for r in base_rows:
                        r.setdefault("vip_name", None)
                        r.setdefault("mobile_raw", None)
                        r.setdefault("store_name", None)
                        r.setdefault("department_brand", None)
                        r.setdefault("tag_names", None)
                    rows = base_rows
                except Exception as e2:
                    return _err(_ex_text(e2, sql_list2), 500, _ex_text(e1, sql_list))

            return _ok({"items": rows, "page": page, "size": size, "total": int(total or 0), "degraded": degraded})

    except Exception as e:
        return _err(_ex_text(e), 500, traceback.format_exc())


@bp.post("/unassigned/assign")
def unassigned_assign():
    """
    body: {"takeover_userid":"U1","external_userids":["ext_a","ext_b",...]}
    - 调试模式（X-Wecom-Debug:1）：本地直落
    - 生产：走 externalcontact/transfer_customer（此处保留 501）
    """
    debug = request.headers.get("X-Wecom-Debug") == "1"
    try:
        body = request.get_json(force=True, silent=False) or {}
    except Exception as e:
        return _bad("invalid json", 400, str(e))

    takeover = (body.get("takeover_userid") or "").strip()
    ext_ids = [x for x in (body.get("external_userids") or []) if str(x or "").strip()]

    if not takeover or not ext_ids:
        return _bad("missing takeover_userid or external_userids")

    if debug:
        try:
            with get_mysql_conn() as conn:
                cur = conn.cursor()
                accepted: List[str] = []
                for ext_id in ext_ids:
                    _exec(
                        cur,
                        "INSERT IGNORE INTO wecom_ops.ext_contact_follow (external_userid, userid) VALUES (%s, %s)",
                        (ext_id, takeover),
                    )
                    _exec(
                        cur,
                        "UPDATE wecom_ops.ext_contact SET is_unassigned=0, updated_at=NOW() WHERE external_userid=%s",
                        (ext_id,),
                    )
                    _exec(
                        cur,
                        """
                        UPDATE wecom_ops.ext_unassigned
                           SET is_active=0, handover_userid=%s, updated_at=NOW()
                         WHERE external_userid=%s
                        """,
                        (takeover, ext_id),
                    )
                    accepted.append(ext_id)
                conn.commit()
            return _ok({"mode": "debug_local", "count": len(accepted), "accepted": accepted, "skipped": []})
        except Exception as e:
            return _err(_ex_text(e), 500, traceback.format_exc())

    return _bad("live assign not implemented; use debug mode or enable upstream transfer api", 501)
