from flask import Blueprint, request, jsonify, g
from app.core.db import get_mysql_conn as get_conn
import json, math, traceback
from datetime import datetime

bp = Blueprint("mass_v1", __name__, url_prefix="/api/v1/mass")

# 新增代码开始
from app.core.db import get_mysql_conn

# --- status code mapping (DB uses int, API returns str) ---
STATUS_MAP = {'INIT':0,'PLANNED':1,'RUNNING':2,'DONE':3,'FAILED':4}
REV_STATUS = {v:k for k,v in STATUS_MAP.items()}
INIT=STATUS_MAP['INIT']
PLANNED=STATUS_MAP['PLANNED']
RUNNING=STATUS_MAP['RUNNING']
DONE=STATUS_MAP['DONE']
FAILED=STATUS_MAP['FAILED']

def status_code(x):
    try:
        return int(x)
    except Exception:
        return STATUS_MAP.get(str(x).upper(), 0)
def status_name(x):
    try:
        return REV_STATUS.get(int(x), 'INIT')
    except Exception:
        return 'INIT'

def _row_values(row):
    if row is None:
        return []
    if isinstance(row, dict):
        return list(row.values())
    return list(row)

def _scalar(row, default=None):
    vals = _row_values(row)
    return vals[0] if vals else default

from flask import jsonify, g

def _json_ok(data, status=200):
    resp = jsonify({"ok": True, "data": data})
    resp.headers["X-Request-Id"] = getattr(g, "trace_id", "")
    return resp, status

def _json_err(code, message, detail="", status=500):
    resp = jsonify({"ok": False, "error": {"code": code, "message": message, "detail": detail}})
    resp.headers["X-Request-Id"] = getattr(g, "trace_id", "")
    return resp, status

def _first_pending_wave(cur, task_id: int):
    cur.execute(
        "SELECT MIN(wave_no) FROM wecom_ops.mass_target_snapshot "
        "WHERE task_id=%s AND state IN ('pending','planned','running')",
        (task_id,)
    )
    row = cur.fetchone()
    val = _scalar(row)
    return val if val is not None else None

def _count_by_state(cur, task_id: int, wave_no: int | None = None):
    if wave_no is None:
        cur.execute("SELECT state, COUNT(*) FROM wecom_ops.mass_target_snapshot WHERE task_id=%s GROUP BY state", (task_id,))
    else:
        cur.execute("SELECT state, COUNT(*) FROM wecom_ops.mass_target_snapshot WHERE task_id=%s AND wave_no=%s GROUP BY state",
                    (task_id, wave_no))
    m = {}
    rows = cur.fetchall()
    for r in rows:
        v = _row_values(r)
        if not v: continue
        key = v[0]
        val = int(v[1]) if len(v) > 1 and v[1] is not None else 0
        m[key] = val
    for k in ("pending","planned","running","done","failed","recalled"):
        m.setdefault(k, 0)
    return m

def _set_task_status(cur, task_id: int, status_str: str):
    cur.execute("UPDATE wecom_ops.mass_task SET status=%s, updated_at=NOW() WHERE id=%s", (status_code(status_str), task_id))

@bp.post("/tasks/<int:task_id>/run")
def run_task(task_id: int):
    try:
        conn = get_mysql_conn()
        with conn.cursor() as cur:
            # 任务是否存在
            cur.execute("SELECT status FROM wecom_ops.mass_task WHERE id=%s", (task_id,))
            r = cur.fetchone()
            if not r:
                return _json_err("NOT_FOUND", f"task {task_id} not found", status=404)
            status_now = _scalar(r)

            # 找到当前最小未完成波次
            wave = _first_pending_wave(cur, task_id)
            if wave is None:
                _set_task_status(cur, task_id, DONE)
                conn.commit()
                return _json_ok({"task_id": task_id, "status": "DONE", "message": "no waves left"})

            # 置任务 RUNNING
            _set_task_status(cur, task_id, RUNNING)

            # 将该波所有 pending/planned/running 直接落成 done（模拟发送完成）
            cur.execute(
                "UPDATE wecom_ops.mass_target_snapshot "
                "SET state='done', updated_at=NOW() "
                "WHERE task_id=%s AND wave_no=%s AND state IN ('pending','planned','running')",
                (task_id, wave)
            )
            cur.execute(
                "SELECT COUNT(*) FROM wecom_ops.mass_target_snapshot "
                "WHERE task_id=%s AND wave_no=%s AND state='done'",
                (task_id, wave)
            )
            done_cnt = int((_scalar(cur.fetchone()) or 0))

            # 若已经没有剩余波次，顺便把任务置为 DONE
            nxt = _first_pending_wave(cur, task_id)
            if nxt is None:
                _set_task_status(cur, task_id, DONE)

            # 统计
            by_wave = _count_by_state(cur, task_id, wave)
            by_all  = _count_by_state(cur, task_id)
            conn.commit()

            return _json_ok({
                "task_id": task_id,
                "wave_no": wave,
                "changed_to_done": done_cnt,
                "by_wave": by_wave,
                "by_all": by_all,
                "status": "DONE" if nxt is None else "RUNNING"
            })
    except Exception as e:
        return _json_err("INTERNAL_ERROR", str(e))

@bp.post("/tasks/<int:task_id>/promote")
def promote_task(task_id: int):
    # 语义与 run 相同：推进“下一波”。为简单起见等价于 run。
    return run_task(task_id)
# 新增代码结束

def j_ok(data, http=200):
    resp = jsonify({"ok": True, "data": data})
    try: resp.headers.setdefault("X-Request-Id", getattr(g, "trace_id",""))
    except: pass
    return resp, http

def j_err(code, message, detail="", http=500):
    resp = jsonify({"ok": False, "error": {"code": code, "message": message, "detail": detail}})
    try: resp.headers.setdefault("X-Request-Id", getattr(g, "trace_id",""))
    except: pass
    return resp, http

# 以下为原有代码（从_list_param函数开始保持不变）
def _list_param(obj, key):
    v = obj.get(key)
    if v is None: return []
    if isinstance(v, list): return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v, str):
        if "," in v: return [s.strip() for s in v.split(",") if s.strip()]
        return [v.strip()] if v.strip() else []
    return []

# ------- 目标集合 SQL 生成（FILTER / UPLOAD / MIXED） -------
def _filter_sql(filters):
    where = []
    args  = []
    # has_unionid
    has_uid = filters.get("has_unionid")
    if has_uid is not None:
        where.append("(e.unionid IS NOT NULL AND e.unionid<>'')") if int(has_uid)==1 else where.append("(e.unionid IS NULL OR e.unionid='')")
    # q 模糊
    q = (filters.get("q") or "").strip()
    if q:
        where.append("(e.name LIKE %s OR e.corp_name LIKE %s)")
        args += [f"%{q}%", f"%{q}%"]
    # owner_userids（按跟进人过滤）
    owners = _list_param(filters, "owner_userids")
    if owners:
        where.append("e.follow_userid IN ("+ ",".join(["%s"]*len(owners)) +")")
        args += owners
    # tag_ids（存在关联）
    tag_ids = _list_param(filters, "tag_ids")
    if tag_ids:
        where.append("EXISTS (SELECT 1 FROM wecom_ops.ext_contact_tag t WHERE t.external_userid=e.external_userid AND t.tag_id IN ("+ ",".join(["%s"]*len(tag_ids)) +"))")
        args += tag_ids

    sql = "SELECT e.external_userid FROM wecom_ops.ext_contact e"
    if where: sql += " WHERE " + " AND ".join(where)
    return sql, tuple(args)

def _upload_sql(upload_id):
    sql = """
      SELECT v.external_userid
      FROM wecom_ops.mobile_upload_item i
      JOIN wecom_ops.vw_mobile_to_external v
        ON v.mobile_std = i.mobile_std
      WHERE i.upload_id = %s
    """
    return sql, (int(upload_id),)

def _combine_targets_sql(spec):
    """
    returns: (sql_text, params_tuple)
    """
    mode = (spec.get("mode") or "FILTER").upper()
    if mode == "FILTER":
        return _filter_sql(spec.get("filters") or {})
    elif mode == "UPLOAD":
        upid = spec.get("upload_id")
        if not upid: raise ValueError("upload_id required for UPLOAD mode")
        return _upload_sql(upid)
    elif mode == "MIXED":
        filters = spec.get("filters") or {}
        upid    = spec.get("upload_id")
        if not upid: raise ValueError("upload_id required for MIXED mode")
        f_sql, f_args = _filter_sql(filters)
        u_sql, u_args = _upload_sql(upid)
        sql  = "SELECT DISTINCT external_userid FROM ( " + f_sql + " UNION ALL " + u_sql + " ) AS x"
        args = f_args + u_args
        return sql, args
    else:
        raise ValueError(f"unknown mode: {mode}")

# ------- B6 覆盖预估 -------
@bp.post("/targets/estimate")
def estimate_targets():
    try:
        body = request.get_json(force=True) or {}
        mode = (body.get("mode") or "FILTER").upper()
        conn = get_conn()
        with conn.cursor() as cur:
            if mode == "MIXED":
                # MIXED模式：计算筛选集与上传集的交集
                filters = body.get("filters") or {}
                upload_id = body.get("upload_id")
                if not upload_id:
                    raise ValueError("upload_id required for MIXED mode")
                
                # 生成筛选集和上传集的子查询
                f_sql, f_args = _filter_sql(filters)
                u_sql, u_args = _upload_sql(upload_id)
                
                # 计算交集数量（两侧先去重再关联）
                intersect_query = f"""
                SELECT COUNT(*) AS cnt
                FROM (
                  SELECT DISTINCT external_userid
                  FROM ({f_sql}) AS f0
                ) AS f
                JOIN (
                  SELECT DISTINCT external_userid
                  FROM ({u_sql}) AS u0
                ) AS u
                  ON u.external_userid = f.external_userid
                """
                cur.execute(intersect_query, f_args + u_args)
                cnt_row = cur.fetchone()
                cnt = int(cnt_row.get('cnt') if isinstance(cnt_row, dict) else cnt_row[0]) or 0
                total = cnt
                
                # 计算筛选集和上传集各自的数量（可选明细）
                cur.execute(f"SELECT COUNT(DISTINCT external_userid) AS cnt FROM ({f_sql}) x", f_args)
                n_f_row = cur.fetchone()
                n_f = int(n_f_row.get('cnt') if isinstance(n_f_row, dict) else n_f_row[0]) or 0
                
                cur.execute(f"SELECT COUNT(DISTINCT external_userid) AS cnt FROM ({u_sql}) x", u_args)
                n_u_row = cur.fetchone()
                n_u = int(n_u_row.get('cnt') if isinstance(n_u_row, dict) else n_u_row[0]) or 0
                
                by = {
                    "mixed": cnt,
                    "filter": n_f,
                    "upload": n_u
                }
            else:
                # FILTER/UPLOAD模式保持原有逻辑
                # 总量计算
                total_sql, total_args = _combine_targets_sql(body)
                cur.execute(f"SELECT COUNT(DISTINCT external_userid) AS cnt FROM ({total_sql}) t", total_args)
                row = cur.fetchone()
                total = int(row.get('cnt') if isinstance(row, dict) else row[0])

                # 分项统计
                by = {}
                if mode in ("FILTER", "MIXED"):
                    f_sql, f_args = _filter_sql(body.get("filters") or {})
                    cur.execute(f"SELECT COUNT(DISTINCT external_userid) AS cnt FROM ({f_sql}) t", f_args)
                    r = cur.fetchone()
                    by["filter"] = int(r.get('cnt') if isinstance(r, dict) else r[0])
                if mode in ("UPLOAD", "MIXED"):
                    u_sql, u_args = _upload_sql(body.get("upload_id"))
                    cur.execute(f"SELECT COUNT(DISTINCT external_userid) AS cnt FROM ({u_sql}) t", u_args)
                    r = cur.fetchone()
                    by["upload"] = int(r.get('cnt') if isinstance(r, dict) else r[0])
                if mode == "MIXED":
                    # 原MIXED的intersect逻辑已移除，统一由上方MIXED分支处理
                    pass

        return j_ok({"total": total, "by": by})
    except Exception as e:
        return j_err("INTERNAL_ERROR", str(e), traceback.format_exc(), 500)
# ------- B1 创建任务 -------
@bp.post("/tasks")
def create_task():
    try:
        body = request.get_json(force=True) or {}
        name = body.get("name") or "任务"
        content_type = body.get("content_type") or "text"
        content_json = json.dumps(body.get("content_json") or {}, ensure_ascii=False)
        targets_spec = json.dumps(body.get("targets_spec") or {}, ensure_ascii=False)

        qps_limit = int(body.get("qps_limit") or 300)
        conc      = int(body.get("concurrency_limit") or 20)
        batch_sz  = int(body.get("batch_size") or 500)
        agent_id  = body.get("agent_id")
        sched     = (body.get("scheduled_at") or "").strip()

        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("""
              INSERT INTO wecom_ops.mass_task
              (task_no, name, content_type, content_json, targets_spec, status,
               qps_limit, concurrency_limit, batch_size, agent_id, scheduled_at, created_at, updated_at)
              VALUES (%s,%s,%s,%s,%s, 0, %s,%s,%s,%s, %s, NOW(), NOW())
            """, (body.get("task_no"), name, content_type, content_json, targets_spec,
                  qps_limit, conc, batch_sz, agent_id, sched or None))
            task_id = cur.lastrowid
        return j_ok({"task_id": int(task_id)}, 201)
    except Exception as e:
        return j_err("INTERNAL_ERROR", str(e), traceback.format_exc(), 500)

# ------- B2 规划 -------
@bp.post("/tasks/<int:task_id>/plan")
def plan_task(task_id: int):
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            # 取任务
            cur.execute("SELECT id, batch_size, targets_spec FROM wecom_ops.mass_task WHERE id=%s", (task_id,))
            row = cur.fetchone()
            if not row:
                return j_err("NOT_FOUND", f"task {task_id} not found", "", 404)
            batch_size = int(row.get('batch_size') if isinstance(row, dict) else row[1])
            spec = row.get('targets_spec') if isinstance(row, dict) else row[2]
            spec = json.loads(spec or "{}")

            # 拉取目标 external_userid（distinct）
            sql, args = _combine_targets_sql(spec)
            cur.execute(f"SELECT DISTINCT external_userid FROM ({sql}) s", args)
            recips = [r['external_userid'] if isinstance(r, dict) else r[0] for r in cur.fetchall()]

            # 物化到 snapshot（清理旧的 pending/planned，再写入）
            cur.execute("DELETE FROM wecom_ops.mass_target_snapshot WHERE task_id=%s", (task_id,))
            total = len(recips)
            if total:
                wave_no = 1
                batches = math.ceil(total / batch_size)
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                B = 1000
                idx = 0
                for b in range(1, batches+1):
                    chunk = recips[idx: idx+batch_size]; idx += batch_size
                    vals = [(task_id, r, 'pending', wave_no, b, now, now) for r in chunk]
                    for i in range(0, len(vals), B):
                        cur.executemany("""
                          INSERT INTO wecom_ops.mass_target_snapshot
                          (task_id, recipient_id, state, wave_no, batch_no, created_at, updated_at)
                          VALUES (%s,%s,%s,%s,%s,%s,%s)
                        """, vals[i:i+B])

                # 更新任务状态
                cur.execute("UPDATE wecom_ops.mass_task SET status=1, updated_at=NOW() WHERE id=%s", (task_id,))
                plan = {"total": total, "waves": { "1": {"batches": batches, "size": batch_size} } }
            else:
                plan = {"total": 0, "waves": {}}

        return j_ok({"plan": plan})
    except Exception as e:
        return j_err("INTERNAL_ERROR", str(e), traceback.format_exc(), 500)

# ------- B4 目标分页（保持不变） -------
@bp.get("/tasks/<int:task_id>/targets")
def list_targets(task_id: int):
    try:
        page = int(request.args.get("page", 1)); size = int(request.args.get("size", 20))
        state = (request.args.get("state") or "").strip()
        off = (page-1)*size
        conn = get_conn()
        with conn.cursor() as cur:
            cond = ["task_id=%s"]; args=[task_id]
            if state:
                cond.append("state=%s"); args.append(state.lower())
            where = " AND ".join(cond)

            cur.execute(f"SELECT COUNT(*) AS cnt FROM wecom_ops.mass_target_snapshot WHERE {where}", tuple(args))
            row = cur.fetchone(); total = int(row.get('cnt') if isinstance(row, dict) else row[0])

            cur.execute(f"""
              SELECT recipient_id, state, wave_no, batch_no, created_at, updated_at
              FROM wecom_ops.mass_target_snapshot
              WHERE {where}
              ORDER BY wave_no, batch_no, recipient_id
              LIMIT %s OFFSET %s
            """, tuple(args+[size, off]))
            items = []
            for r in cur.fetchall():
                d = r if isinstance(r, dict) else {
                    "recipient_id": r[0], "state": r[1], "wave_no": r[2],
                    "batch_no": r[3], "created_at": r[4].strftime("%Y-%m-%d %H:%M:%S") if r[4] else None,
                    "updated_at": r[5].strftime("%Y-%m-%d %H:%M:%S") if r[5] else None,
                }
                if isinstance(r, dict):
                    d["created_at"] = (r.get("created_at") or "").strftime("%Y-%m-%d %H:%M:%S") if r.get("created_at") else None
                    d["updated_at"] = (r.get("updated_at") or "").strftime("%Y-%m-%d %H:%M:%S") if r.get("updated_at") else None
                items.append(d)

        return j_ok({"items": items, "total": total, "page": page, "size": size})
    except Exception as e:
        return j_err("INTERNAL_ERROR", str(e), traceback.format_exc(), 500)

# ------- B5 重试失败（保持不变｜按需可扩展） -------
@bp.post("/tasks/<int:task_id>/retry_failed")
def retry_failed(task_id: int):
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("""
              UPDATE wecom_ops.mass_target_snapshot
                 SET state='pending', updated_at=NOW()
               WHERE task_id=%s AND state='failed'
            """, (task_id,))
            reset = cur.rowcount
        return j_ok({"task_id": task_id, "reset": int(reset)})
    except Exception as e:
        return j_err("INTERNAL_ERROR", str(e), traceback.format_exc(), 500)

# ------- B1/B4 列表（保持已有语义） -------
@bp.get("/tasks")
def list_tasks():
    try:
        page = int(request.args.get("page", 1)); size = int(request.args.get("size", 20))
        off = (page-1)*size
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS cnt FROM wecom_ops.mass_task")
            row = cur.fetchone(); total = int(row.get('cnt') if isinstance(row, dict) else row[0])

            cur.execute("""
              SELECT id, task_no, name, content_type, status, agent_id,
                     qps_limit, concurrency_limit, batch_size, scheduled_at,
                     created_at, updated_at
                FROM wecom_ops.mass_task
               ORDER BY id DESC
               LIMIT %s OFFSET %s
            """, (size, off))
            items=[]
            for r in cur.fetchall():
                if isinstance(r, dict):
                    d = {
                      "id": r["id"], "task_no": r["task_no"], "name": r["name"],
                      "content_type": r["content_type"], "status": status_name(r["status"]),
                      "agent_id": r["agent_id"], "qps_limit": r["qps_limit"], "concurrency_limit": r["concurrency_limit"], "batch_size": r["batch_size"],
                      "scheduled_at": r["scheduled_at"] or "",
                      "created_at": r["created_at"].strftime("%Y-%m-%d %H:%M:%S") if r["created_at"] else "",
                      "updated_at": r["updated_at"].strftime("%Y-%m-%d %H:%M:%S") if r["updated_at"] else "",
                    }
                else:
                    d = {
                      "id": r[0], "task_no": r[1], "name": r[2], "content_type": r[3],
                      "status": status_name(r[4]),
                      "agent_id": r[5], "qps_limit": r[6], "concurrency_limit": r[7], "batch_size": r[8],
                      "scheduled_at": r[9] or "",
                      "created_at": r[10].strftime("%Y-%m-%d %H:%M:%S") if r[10] else "",
                      "updated_at": r[11].strftime("%Y-%m-%d %H:%M:%S") if r[11] else "",
                    }
                items.append(d)
        return j_ok({"items": items, "total": total, "page": page, "size": size})
    except Exception as e:
        return j_err("INTERNAL_ERROR", str(e), traceback.format_exc(), 500)