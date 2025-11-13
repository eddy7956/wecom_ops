# -*- coding: utf-8 -*-
"""企业员工与外部联系人身份映射服务。"""

from contextlib import contextmanager
from typing import Iterator

from app.core.db import get_mysql_conn


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


def get_union_mapping(employee_id: str | None = None, external_userid: str | None = None) -> dict:
    with _use_cursor() as cur:
        if employee_id:
            cur.execute(
                """
                SELECT ec.external_userid, ec.name AS ext_name
                FROM ext_follow_user ef
                JOIN ext_contact ec ON ec.external_userid = ef.external_userid
                WHERE ef.userid = %s
                """,
                (employee_id,),
            )
            return {"employee_id": employee_id, "contacts": cur.fetchall()}
        if external_userid:
            cur.execute(
                """
                SELECT ef.userid AS owner_userid, oe.name AS owner_name
                FROM ext_follow_user ef
                LEFT JOIN org_employee oe ON oe.userid = ef.userid
                WHERE ef.external_userid = %s
                """,
                (external_userid,),
            )
            return {"external_userid": external_userid, "owners": cur.fetchall()}
    return {}


def list_bi_views(view: str = "vw_contact_identity", page: int = 1, size: int = 50) -> dict:
    offset = (page - 1) * size
    with _use_cursor() as cur:
        cur.execute(f"SELECT SQL_CALC_FOUND_ROWS * FROM {view} LIMIT %s,%s", (offset, size))
        rows = cur.fetchall()
        cur.execute("SELECT FOUND_ROWS() AS n")
        total = cur.fetchone()["n"]
    return {"items": rows, "total": total, "page": page, "size": size}
