# -*- coding: utf-8 -*-
"""外部联系人同步与查询服务。"""

import json
import time
from contextlib import contextmanager
from typing import Iterator

from app.core.db import get_mysql_conn
from app.wecom.client import wecom_get_json, wecom_post_json


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


def _employees() -> list[str]:
    with _use_cursor() as cur:
        cur.execute("SELECT userid FROM org_employee WHERE enable=1 OR enable IS NULL")
        return [row["userid"] for row in cur.fetchall()]


def sync_contacts(full: bool = False, throttle_ms: int = 200) -> dict:
    up_contact = up_follow = up_tagrel = 0
    with _use_cursor() as cur:
        for userid in _employees():
            listing = wecom_get_json(
                "https://qyapi.weixin.qq.com/cgi-bin/externalcontact/list",
                "ext",
                params={"userid": userid},
            )
            for external_userid in listing.get("external_userid", []):
                detail = wecom_get_json(
                    "https://qyapi.weixin.qq.com/cgi-bin/externalcontact/get",
                    "ext",
                    params={"external_userid": external_userid},
                )
                info = detail.get("external_contact", {})
                follow_users = detail.get("follow_user", [])
                cur.execute(
                    """
                    REPLACE INTO ext_contact
                        (external_userid, name, corp_full_name, position, gender, unionid, ext)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        info.get("external_userid") or external_userid,
                        info.get("name"),
                        info.get("corp_full_name"),
                        info.get("position"),
                        info.get("gender"),
                        info.get("unionid"),
                        json.dumps(info, ensure_ascii=False),
                    ),
                )
                up_contact += 1
                for follow in follow_users:
                    cur.execute(
                        """
                        REPLACE INTO ext_follow_user
                            (external_userid, userid, remark, state, add_way, create_time)
                        VALUES (%s, %s, %s, %s, %s, FROM_UNIXTIME(%s))
                        """,
                        (
                            external_userid,
                            follow.get("userid"),
                            follow.get("remark"),
                            follow.get("state"),
                            follow.get("add_way"),
                            follow.get("createtime") or 0,
                        ),
                    )
                    for tag_id in follow.get("tags") or []:
                        cur.execute(
                            """REPLACE INTO ext_contact_tag (external_userid, tag_id) VALUES (%s, %s)""",
                            (external_userid, tag_id),
                        )
                        up_tagrel += 1
                    up_follow += 1
            time.sleep(throttle_ms / 1000.0)
    return {
        "contacts_upserted": up_contact,
        "follow_upserted": up_follow,
        "tag_relations": up_tagrel,
    }


def sync_tags() -> dict:
    data = wecom_post_json(
        "https://qyapi.weixin.qq.com/cgi-bin/externalcontact/get_corp_tag_list",
        "ext",
        body={},
    )
    up = 0
    with _use_cursor() as cur:
        for group in data.get("tag_group", []):
            for tag in group.get("tag", []):
                cur.execute(
                    """
                    REPLACE INTO ext_tag (tag_id, group_id, group_name, name, order_no)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        tag["id"],
                        group.get("group_id"),
                        group.get("group_name"),
                        tag.get("name"),
                        tag.get("order"),
                    ),
                )
                up += 1
    return {"tags_upserted": up}


def list_contacts(tag: str | None = None, owner: str | None = None, page: int = 1, size: int = 50) -> dict:
    offset = (page - 1) * size
    with _use_cursor() as cur:
        if tag and owner:
            sql = """
                SELECT SQL_CALC_FOUND_ROWS ec.* FROM ext_contact ec
                JOIN ext_follow_user ef ON ef.external_userid = ec.external_userid
                JOIN ext_contact_tag et ON et.external_userid = ec.external_userid
                WHERE ef.userid = %s AND et.tag_id = %s
                ORDER BY ec.external_userid LIMIT %s, %s
            """
            cur.execute(sql, (owner, tag, offset, size))
        elif tag:
            sql = """
                SELECT SQL_CALC_FOUND_ROWS ec.* FROM ext_contact ec
                JOIN ext_contact_tag et ON et.external_userid = ec.external_userid
                WHERE et.tag_id = %s ORDER BY ec.external_userid LIMIT %s, %s
            """
            cur.execute(sql, (tag, offset, size))
        elif owner:
            sql = """
                SELECT SQL_CALC_FOUND_ROWS ec.* FROM ext_contact ec
                JOIN ext_follow_user ef ON ef.external_userid = ec.external_userid
                WHERE ef.userid = %s ORDER BY ec.external_userid LIMIT %s, %s
            """
            cur.execute(sql, (owner, offset, size))
        else:
            cur.execute(
                """
                SELECT SQL_CALC_FOUND_ROWS * FROM ext_contact
                ORDER BY external_userid LIMIT %s, %s
                """,
                (offset, size),
            )
        rows = cur.fetchall()
        cur.execute("SELECT FOUND_ROWS() AS n")
        total = cur.fetchone()["n"]
    return {"items": rows, "total": total, "page": page, "size": size}
