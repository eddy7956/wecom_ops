import json
from app.core.db import get_mysql_conn

def _loads(j):
    if j is None: return None
    if isinstance(j, (dict, list)): return j
    try: return json.loads(j)
    except: return None

def create_task_row(task: dict) -> int:
    sql = """INSERT INTO mass_task
        (task_no, name, mass_type, content_type, content_json, targets_spec,
         status, scheduled_at, qps_limit, concurrency_limit, batch_size,
         gray_strategy, report_stat, agent_id)
        VALUES (%s,%s,%s,%s,%s,%s,0,%s,%s,%s,%s,%s,%s,%s)"""
    args = (
        task.get("task_no"),
        task.get("name"),
        task.get("mass_type","external"),
        task["content_type"],
        json.dumps(task.get("content_json") or {}, ensure_ascii=False),
        json.dumps(task.get("targets_spec") or {}, ensure_ascii=False),
        task.get("scheduled_at"),
        task.get("qps_limit"),
        task.get("concurrency_limit"),
        task.get("batch_size"),
        json.dumps(task.get("gray_strategy") or {}, ensure_ascii=False),
        json.dumps(task.get("report_stat") or {}, ensure_ascii=False),
        task.get("agent_id"),
    )
    conn = get_mysql_conn(); cur = conn.cursor()
    cur.execute(sql, args); conn.commit()
    tid = cur.lastrowid
    cur.close(); conn.close()
    return tid

def get_task_row(task_id: int):
    sql = "SELECT * FROM mass_task WHERE id=%s"
    conn = get_mysql_conn(); cur = conn.cursor()
    cur.execute(sql, (task_id,)); row = cur.fetchone()
    cur.close(); conn.close()
    if not row: return None
    row["content_json"]  = _loads(row.get("content_json"))
    row["targets_spec"]  = _loads(row.get("targets_spec"))
    row["gray_strategy"] = _loads(row.get("gray_strategy"))
    row["report_stat"]   = _loads(row.get("report_stat"))
    return row

def update_task_fields(task_id: int, fields: dict):
    sets, args = [], []
    for k in ("name","scheduled_at","qps_limit","concurrency_limit","batch_size"):
        if k in fields:
            sets.append(f"{k}=%s"); args.append(fields[k])
    for k in ("content_json","targets_spec","gray_strategy","report_stat"):
        if k in fields:
            sets.append(f"{k}=%s")
            args.append(json.dumps(fields[k], ensure_ascii=False))
    if not sets: return
    sql = "UPDATE mass_task SET "+",".join(sets)+", updated_at=NOW() WHERE id=%s"
    args.append(task_id)
    conn = get_mysql_conn(); cur = conn.cursor()
    cur.execute(sql, tuple(args)); conn.commit()
    cur.close(); conn.close()

def set_task_status(task_id: int, status: int):
    conn = get_mysql_conn(); cur = conn.cursor()
    cur.execute("UPDATE mass_task SET status=%s, updated_at=NOW() WHERE id=%s",(status,task_id))
    conn.commit(); cur.close(); conn.close()

def delete_task(task_id: int):
    conn = get_mysql_conn(); cur = conn.cursor()
    cur.execute("DELETE FROM mass_target_snapshot WHERE task_id=%s",(task_id,))
    cur.execute("DELETE FROM mass_task WHERE id=%s",(task_id,))
    conn.commit(); cur.close(); conn.close()

def insert_snapshots(task_id: int, rows: list[dict]) -> int:
    if not rows: return 0
    sql = """INSERT INTO mass_target_snapshot
             (task_id, recipient_id, shard_no, wave_no, batch_no, state)
             VALUES (%s,%s,%s,%s,%s,%s)"""
    args = [(task_id, r["recipient_id"], r.get("shard_no",0),
             r["wave_no"], r["batch_no"], "pending") for r in rows]
    conn = get_mysql_conn(); cur = conn.cursor()
    cur.executemany(sql, args); n = cur.rowcount
    conn.commit(); cur.close(); conn.close()
    return n

def page_snapshots(task_id: int, state: str|None, page: int, size: int):
    where = ["task_id=%s"]; args=[task_id]
    if state: where.append("state=%s"); args.append(state)
    where_sql = " AND ".join(where)
    sql_items = f"""
      SELECT recipient_id,wave_no,batch_no,state,last_error
      FROM mass_target_snapshot
      WHERE {where_sql}
      ORDER BY id
      LIMIT %s OFFSET %s"""
    sql_count = f"SELECT COUNT(*) AS c FROM mass_target_snapshot WHERE {where_sql}"
    args_items = args + [size, (page-1)*size]
    conn = get_mysql_conn(); cur = conn.cursor()
    cur.execute(sql_count, tuple(args)); total = cur.fetchone()["c"]
    cur.execute(sql_items, tuple(args_items)); items = cur.fetchall()
    cur.close(); conn.close()
    return {"page":page,"size":size,"total":total,"items":items}

def page_tasks(q: dict):
    page, size = q["page"], q["size"]
    where, args = ["1=1"], []
    if q.get("status"):
        sts = q["status"].split(",")
        where.append("status IN ("+ ",".join(["%s"]*len(sts)) +")")
        args += sts
    if q.get("q"):
        where.append("(task_no LIKE %s OR name LIKE %s)")
        args += [f"%{q['q']}%", f"%{q['q']}%"]
    if q.get("date_from"): where.append("created_at >= %s"); args.append(q["date_from"])
    if q.get("date_to"):   where.append("created_at <= %s"); args.append(q["date_to"])
    where_sql = " AND ".join(where)
    sql_count = f"SELECT COUNT(*) AS c FROM mass_task WHERE {where_sql}"
    sql_items = f"""
      SELECT id,task_no,name,status,scheduled_at,report_stat,created_at
      FROM mass_task
      WHERE {where_sql}
      ORDER BY id DESC
      LIMIT %s OFFSET %s"""
    conn = get_mysql_conn(); cur = conn.cursor()
    cur.execute(sql_count, tuple(args)); total = cur.fetchone()["c"]
    cur.execute(sql_items, tuple(args + [size, (page-1)*size])); items = cur.fetchall()
    cur.close(); conn.close()
    for it in items:
        it["report_stat"] = _loads(it.get("report_stat")) or {}
    return {"page":page,"size":size,"total":total,"items":items}

def list_logs(task_id:int, level:str|None, q:str|None, page:int, size:int):
    where, args = ["task_id=%s"], [task_id]
    if level: where.append("level=%s"); args.append(level)
    if q:     where.append("message LIKE %s"); args.append(f"%{q}%")
    where_sql = " AND ".join(where)
    sql_count = f"SELECT COUNT(*) AS c FROM mass_task_log WHERE {where_sql}"
    sql_items = f"""
      SELECT created_at, level, message
      FROM mass_task_log
      WHERE {where_sql}
      ORDER BY id DESC
      LIMIT %s OFFSET %s"""
    conn = get_mysql_conn(); cur = conn.cursor()
    cur.execute(sql_count, tuple(args)); total = cur.fetchone()["c"]
    cur.execute(sql_items, tuple(args + [size,(page-1)*size])); items = cur.fetchall()
    cur.close(); conn.close()
    return {"page":page,"size":size,"total":total,"items":items}

def pick_all_contacts(limit:int) -> list[str]:
    sql = "SELECT external_userid FROM ext_contact LIMIT %s"
    conn = get_mysql_conn(); cur = conn.cursor()
    cur.execute(sql,(limit,)); rows = cur.fetchall()
    cur.close(); conn.close()
    return [r["external_userid"] for r in rows]

def pick_by_tag_ids(tag_ids:list[str], limit:int) -> list[str]:
    if not tag_ids: return []
    sql = """SELECT DISTINCT external_userid
             FROM ext_contact_tag
             WHERE tag_id IN (""" + ",".join(["%s"]*len(tag_ids)) + """)
             LIMIT %s"""
    args = tag_ids + [limit]
    conn = get_mysql_conn(); cur = conn.cursor()
    cur.execute(sql, tuple(args)); rows = cur.fetchall()
    cur.close(); conn.close()
    return [r["external_userid"] for r in rows]

from app.core.db import get_conn
import json, datetime

def _row_to_task(row):
    # 兼容 JSON/TEXT 两种列类型
    def parse_json(v):
        if v is None: return {}
        if isinstance(v,(dict,list)): return v
        try: return json.loads(v)
        except: return {}
    return {
        "id": row["id"],
        "task_no": row["task_no"],
        "name": row.get("name"),
        "mass_type": row.get("mass_type") or "external",
        "content_type": row.get("content_type"),
        "content_json": parse_json(row.get("content_json")),
        "targets_spec": parse_json(row.get("targets_spec")),
        "status": row.get("status"),
        "scheduled_at": row.get("scheduled_at"),
        "started_at": row.get("started_at"),
        "finished_at": row.get("finished_at"),
        "last_enqueue_at": row.get("last_enqueue_at"),
        "qps_limit": row.get("qps_limit"),
        "concurrency_limit": row.get("concurrency_limit"),
        "batch_size": row.get("batch_size"),
        "gray_strategy": parse_json(row.get("gray_strategy")),
        "report_stat": parse_json(row.get("report_stat")),
        "agent_id": row.get("agent_id"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }

def get_task(task_id:int):
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM mass_task WHERE id=%s", (task_id,))
        row = cur.fetchone()
        return _row_to_task(row) if row else None

from app.core.db import get_conn

def update_task(task_id:int, fields:dict):
    if not fields: return
    cols, vals = zip(*fields.items())
    sets = ", ".join([f"{c}=%s" for c in cols])
    sql = f"UPDATE mass_task SET {sets} WHERE id=%s"
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, (*vals, task_id))
        conn.commit()

from app.core.db import get_conn

def recall_pending_targets(task_id:int)->int:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE mass_target_snapshot SET state='recalled' WHERE task_id=%s AND state='pending'", (task_id,))
        n = cur.rowcount
        conn.commit()
        return n

from app.core.db import get_conn

def aggregate_task_stats(task_id:int)->dict:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT state, COUNT(*) as cnt
            FROM mass_target_snapshot
            WHERE task_id=%s
            GROUP BY state
        """, (task_id,))
        rows = cur.fetchall()
        kv = {r[0]: int(r[1]) for r in rows}
        total = sum(kv.values()) if rows else 0
        return {"task_id": task_id, "total": total, **kv}
