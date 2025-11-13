# -*- coding: utf-8 -*-
"""组织架构同步与查询服务。"""

import json
from contextlib import contextmanager
from typing import Iterator

from app.core.db import get_mysql_conn
from app.wecom.client import wecom_get_json


@contextmanager
def _use_cursor() -> Iterator:
    conn = get_mysql_conn()
    try:
        with conn.cursor() as cur:
            yield cur
    finally:
        try:
            conn.close()
        except Exception:
            pass


def sync_departments(full: bool = False) -> dict:
    data = wecom_get_json("https://qyapi.weixin.qq.com/cgi-bin/department/list", "contacts")
    upserted = 0
    with _use_cursor() as cur:
        for dept in data.get("department", []):
            cur.execute(
                """
                REPLACE INTO org_department
                    (id, name, parent_id, order_no, path, level, status, ext)
                VALUES (%s, %s, %s, %s, %s, %s, 1, %s)
                """,
                (
                    dept["id"],
                    dept.get("name"),
                    dept.get("parentid"),
                    dept.get("order"),
                    None,
                    None,
                    json.dumps(dept, ensure_ascii=False),
                ),
            )
            upserted += 1
    return {"upserted": upserted}


def sync_employees(full: bool = False, root_dept_id: int = 1, fetch_child: int = 1) -> dict:
    data = wecom_get_json(
        "https://qyapi.weixin.qq.com/cgi-bin/user/list",
        "contacts",
        params={"department_id": root_dept_id, "fetch_child": fetch_child},
    )
    upserted = 0
    with _use_cursor() as cur:
        for user in data.get("userlist", []):
            cur.execute(
                """
                REPLACE INTO org_employee
                    (userid, name, mobile, email, position, gender, enable, qr_code, departments, ext)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user["userid"],
                    user.get("name"),
                    user.get("mobile"),
                    user.get("email"),
                    user.get("position"),
                    user.get("gender"),
                    user.get("enable"),
                    user.get("qr_code"),
                    json.dumps(user.get("department", [])),
                    json.dumps(user, ensure_ascii=False),
                ),
            )
            cur.execute("DELETE FROM org_employee_dept WHERE userid=%s", (user["userid"],))
            for dept_id in user.get("department", []):
                cur.execute(
                    "INSERT IGNORE INTO org_employee_dept (userid, dept_id) VALUES (%s, %s)",
                    (user["userid"], dept_id),
                )
            upserted += 1
    return {"upserted": upserted}


def list_departments(page: int = 1, size: int = 50) -> dict:
    offset = (page - 1) * size
    with _use_cursor() as cur:
        cur.execute(
            "SELECT * FROM org_department ORDER BY parent_id, order_no LIMIT %s,%s",
            (offset, size),
        )
        rows = cur.fetchall()
        cur.execute("SELECT COUNT(*) AS n FROM org_department")
        total = cur.fetchone()["n"]
    return {"items": rows, "total": total, "page": page, "size": size}


def list_employees(dept_id: int | None = None, page: int = 1, size: int = 50) -> dict:
    offset = (page - 1) * size
    with _use_cursor() as cur:
        if dept_id:
            cur.execute(
                """
                SELECT e.* FROM org_employee e
                JOIN org_employee_dept m ON m.userid = e.userid
                WHERE m.dept_id = %s
                ORDER BY e.userid LIMIT %s,%s
                """,
                (dept_id, offset, size),
            )
            rows = cur.fetchall()
            cur.execute("SELECT COUNT(*) AS n FROM org_employee_dept WHERE dept_id=%s", (dept_id,))
            total = cur.fetchone()["n"]
        else:
            cur.execute("SELECT * FROM org_employee ORDER BY userid LIMIT %s,%s", (offset, size))
            rows = cur.fetchall()
            cur.execute("SELECT COUNT(*) AS n FROM org_employee")
            total = cur.fetchone()["n"]
    return {"items": rows, "total": total, "page": page, "size": size}
