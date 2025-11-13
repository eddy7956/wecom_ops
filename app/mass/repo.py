"""Data access helpers for mass messaging domain."""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any, Dict, List, Sequence

from pymysql.err import IntegrityError

from app.core.db import get_mysql_conn


class DuplicateTaskNoError(Exception):
    """Raised when task_no conflicts with an existing record."""


@contextmanager
def _use_cursor():
    conn = get_mysql_conn()
    try:
        with conn.cursor() as cur:
            yield conn, cur
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _loads_json(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return None


def _dump_json(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False)


def _format_dt(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        return value.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(value)


def _normalize_task(row: Dict[str, Any]) -> Dict[str, Any]:
    task = dict(row)
    for key in ("content_json", "targets_spec", "gray_strategy", "report_stat"):
        task[key] = _loads_json(task.get(key)) or {}
    for key in ("scheduled_at", "started_at", "finished_at", "last_enqueue_at", "created_at", "updated_at"):
        task[key] = _format_dt(task.get(key))
    return task


def create_task(task: Dict[str, Any]) -> int:
    sql = (
        """
        INSERT INTO mass_task
            (task_no, name, mass_type, content_type, content_json, targets_spec,
             status, scheduled_at, qps_limit, concurrency_limit, batch_size,
             gray_strategy, report_stat, agent_id)
        VALUES (%s, %s, %s, %s, %s, %s,
                0, %s, %s, %s, %s, %s, %s, %s)
        """
    )
    args = (
        task.get("task_no"),
        task.get("name"),
        task.get("mass_type", "external"),
        task["content_type"],
        _dump_json(task.get("content_json")),
        _dump_json(task.get("targets_spec")),
        task.get("scheduled_at"),
        task.get("qps_limit"),
        task.get("concurrency_limit"),
        task.get("batch_size"),
        _dump_json(task.get("gray_strategy")),
        _dump_json(task.get("report_stat")),
        task.get("agent_id"),
    )
    try:
        with _use_cursor() as (conn, cur):
            cur.execute(sql, args)
            task_id = cur.lastrowid
            conn.commit()
            return int(task_id)
    except IntegrityError as exc:  # pragma: no cover - depends on DB schema
        raise DuplicateTaskNoError from exc


def get_task(task_id: int) -> Dict[str, Any] | None:
    with _use_cursor() as (_, cur):
        cur.execute("SELECT * FROM mass_task WHERE id=%s", (task_id,))
        row = cur.fetchone()
    return _normalize_task(row) if row else None


def get_task_by_no(task_no: str) -> Dict[str, Any] | None:
    with _use_cursor() as (_, cur):
        cur.execute("SELECT * FROM mass_task WHERE task_no=%s", (task_no,))
        row = cur.fetchone()
    return _normalize_task(row) if row else None


def update_task(task_id: int, fields: Dict[str, Any]) -> None:
    if not fields:
        return
    sets: List[str] = []
    args: List[Any] = []
    json_fields = {"content_json", "targets_spec", "gray_strategy", "report_stat"}
    for key, value in fields.items():
        if key in json_fields:
            sets.append(f"{key}=%s")
            args.append(_dump_json(value))
        else:
            sets.append(f"{key}=%s")
            args.append(value)
    sets.append("updated_at=NOW()")
    sql = "UPDATE mass_task SET " + ", ".join(sets) + " WHERE id=%s"
    args.append(task_id)
    with _use_cursor() as (conn, cur):
        cur.execute(sql, tuple(args))
        conn.commit()


def set_task_status(task_id: int, status: int, extra: Dict[str, Any] | None = None) -> None:
    update = {"status": status}
    if extra:
        update.update(extra)
    update_task(task_id, update)


def delete_task(task_id: int) -> None:
    with _use_cursor() as (conn, cur):
        cur.execute("DELETE FROM mass_target_snapshot WHERE task_id=%s", (task_id,))
        cur.execute("DELETE FROM mass_task WHERE id=%s", (task_id,))
        conn.commit()


def clear_snapshots(task_id: int) -> None:
    with _use_cursor() as (conn, cur):
        cur.execute("DELETE FROM mass_target_snapshot WHERE task_id=%s", (task_id,))
        conn.commit()


def insert_snapshots(task_id: int, rows: Sequence[Dict[str, Any]]) -> int:
    if not rows:
        return 0
    sql = (
        """
        INSERT INTO mass_target_snapshot
            (task_id, recipient_id, shard_no, wave_no, batch_no, state, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
        """
    )
    values = [
        (
            task_id,
            row["recipient_id"],
            row.get("shard_no", 0),
            row.get("wave_no", 1),
            row.get("batch_no", 1),
            row.get("state", "pending"),
        )
        for row in rows
    ]
    with _use_cursor() as (conn, cur):
        cur.executemany(sql, values)
        inserted = cur.rowcount
        conn.commit()
        return int(inserted)


def page_snapshots(task_id: int, state: str | None, page: int, size: int) -> Dict[str, Any]:
    where = ["task_id=%s"]
    args: List[Any] = [task_id]
    if state:
        where.append("state=%s")
        args.append(state)
    where_clause = " AND ".join(where)
    offset = (page - 1) * size
    with _use_cursor() as (_, cur):
        cur.execute(
            f"SELECT COUNT(*) AS cnt FROM mass_target_snapshot WHERE {where_clause}",
            tuple(args),
        )
        total = int(cur.fetchone()["cnt"])
        cur.execute(
            f"""
            SELECT recipient_id, state, wave_no, batch_no, last_error, created_at, updated_at
            FROM mass_target_snapshot
            WHERE {where_clause}
            ORDER BY id
            LIMIT %s OFFSET %s
            """,
            tuple(args + [size, offset]),
        )
        items = cur.fetchall()
    serialized = []
    for row in items:
        item = dict(row)
        for key in ("created_at", "updated_at"):
            item[key] = _format_dt(item.get(key))
        serialized.append(item)
    return {"page": page, "size": size, "total": total, "items": serialized}


def list_logs(task_id: int, level: str | None, keyword: str | None, page: int, size: int) -> Dict[str, Any]:
    where = ["task_id=%s"]
    args: List[Any] = [task_id]
    if level:
        where.append("level=%s")
        args.append(level)
    if keyword:
        where.append("message LIKE %s")
        args.append(f"%{keyword}%")
    where_clause = " AND ".join(where)
    offset = (page - 1) * size
    with _use_cursor() as (_, cur):
        cur.execute(
            f"SELECT COUNT(*) AS cnt FROM mass_task_log WHERE {where_clause}",
            tuple(args),
        )
        total = int(cur.fetchone()["cnt"])
        cur.execute(
            f"""
            SELECT created_at, level, message
            FROM mass_task_log
            WHERE {where_clause}
            ORDER BY id DESC
            LIMIT %s OFFSET %s
            """,
            tuple(args + [size, offset]),
        )
        rows = cur.fetchall()
    serialized = []
    for row in rows:
        item = dict(row)
        item["created_at"] = _format_dt(item.get("created_at"))
        serialized.append(item)
    return {"page": page, "size": size, "total": total, "items": serialized}


def page_tasks(params: Dict[str, Any]) -> Dict[str, Any]:
    page = params.get("page", 1)
    size = params.get("size", 20)
    offset = (page - 1) * size
    where: List[str] = ["1=1"]
    args: List[Any] = []
    status = params.get("status")
    if status:
        statuses = [s.strip() for s in str(status).split(",") if s.strip()]
        if statuses:
            placeholders = ",".join(["%s"] * len(statuses))
            where.append(f"status IN ({placeholders})")
            args.extend(statuses)
    query = params.get("q")
    if query:
        where.append("(task_no LIKE %s OR name LIKE %s)")
        args.extend([f"%{query}%", f"%{query}%"])
    date_from = params.get("date_from")
    if date_from:
        where.append("created_at >= %s")
        args.append(date_from)
    date_to = params.get("date_to")
    if date_to:
        where.append("created_at <= %s")
        args.append(date_to)
    where_clause = " AND ".join(where)
    with _use_cursor() as (_, cur):
        cur.execute(
            f"SELECT COUNT(*) AS cnt FROM mass_task WHERE {where_clause}",
            tuple(args),
        )
        total = int(cur.fetchone()["cnt"])
        cur.execute(
            f"""
            SELECT id, task_no, name, mass_type, content_type, status, scheduled_at,
                   qps_limit, concurrency_limit, batch_size, gray_strategy,
                   report_stat, agent_id, created_at, updated_at
            FROM mass_task
            WHERE {where_clause}
            ORDER BY id DESC
            LIMIT %s OFFSET %s
            """,
            tuple(args + [size, offset]),
        )
        rows = cur.fetchall()
    items = [_normalize_task(row) for row in rows]
    return {"page": page, "size": size, "total": total, "items": items}


def recall_pending_targets(task_id: int) -> int:
    with _use_cursor() as (conn, cur):
        cur.execute(
            """
            UPDATE mass_target_snapshot
            SET state='recalled', updated_at=NOW()
            WHERE task_id=%s AND state='pending'
            """,
            (task_id,),
        )
        affected = cur.rowcount
        conn.commit()
        return int(affected)


def reset_failed_targets(task_id: int) -> int:
    with _use_cursor() as (conn, cur):
        cur.execute(
            """
            UPDATE mass_target_snapshot
            SET state='pending', updated_at=NOW()
            WHERE task_id=%s AND state='failed'
            """,
            (task_id,),
        )
        affected = cur.rowcount
        conn.commit()
        return int(affected)


def aggregate_task_stats(task_id: int) -> Dict[str, Any]:
    with _use_cursor() as (_, cur):
        cur.execute(
            """
            SELECT state, COUNT(*) AS cnt
            FROM mass_target_snapshot
            WHERE task_id=%s
            GROUP BY state
            """,
            (task_id,),
        )
        rows = cur.fetchall()
    stats = {row["state"]: int(row["cnt"]) for row in rows}
    total = sum(stats.values())
    return {"task_id": task_id, "total": total, **stats}


def pick_all_contacts(limit: int) -> List[str]:
    with _use_cursor() as (_, cur):
        cur.execute("SELECT external_userid FROM ext_contact LIMIT %s", (limit,))
        rows = cur.fetchall()
    return [row["external_userid"] for row in rows]


def pick_by_tag_ids(tag_ids: Sequence[str], limit: int) -> List[str]:
    if not tag_ids:
        return []
    placeholders = ",".join(["%s"] * len(tag_ids))
    sql = (
        """
        SELECT DISTINCT external_userid
        FROM ext_contact_tag
        WHERE tag_id IN ("""
        + placeholders
        + ") LIMIT %s"
    )
    args: List[Any] = list(tag_ids) + [limit]
    with _use_cursor() as (_, cur):
        cur.execute(sql, tuple(args))
        rows = cur.fetchall()
    return [row["external_userid"] for row in rows]
