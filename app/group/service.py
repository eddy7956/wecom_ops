# -*- coding: utf-8 -*-
"""客户群拉取服务。"""
from contextlib import contextmanager
from typing import Iterator

from app.core.db import get_mysql_conn
from app.wecom.client import wecom_post_json


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


def sync_groupchats(limit: int = 100) -> dict:
    cursor = None
    up_chat = up_member = 0
    with _use_cursor() as cur:
        while True:
            body = {"status_filter": 0, "owner_filter": {}, "cursor": cursor, "limit": limit}
            listing = wecom_post_json(
                "https://qyapi.weixin.qq.com/cgi-bin/externalcontact/groupchat/list",
                "ext",
                body=body,
            )
            for item in listing.get("group_chat_list", []):
                chat_id = item.get("chat_id")
                detail = wecom_post_json(
                    "https://qyapi.weixin.qq.com/cgi-bin/externalcontact/groupchat/get",
                    "ext",
                    body={"chat_id": chat_id},
                )
                group_chat = detail.get("group_chat", {})
                cur.execute(
                    """
                    REPLACE INTO ec_groupchat
                        (chat_id, name, owner, notice, create_time, status, ext)
                    VALUES (%s, %s, %s, %s, FROM_UNIXTIME(%s), %s, %s)
                    """,
                    (
                        group_chat.get("chat_id"),
                        group_chat.get("name"),
                        group_chat.get("owner"),
                        group_chat.get("notice"),
                        group_chat.get("create_time") or 0,
                        group_chat.get("status"),
                    ),
                )
                up_chat += 1
                for member in group_chat.get("member_list", []):
                    if member.get("type") == 1:
                        member_id, member_type, unionid = member.get("userid"), "employee", None
                    else:
                        member_id, member_type, unionid = (
                            member.get("external_userid"),
                            "external",
                            member.get("unionid"),
                        )
                    cur.execute(
                        """
                        REPLACE INTO ec_groupchat_member
                            (chat_id, member_id, member_type, join_time, unionid)
                        VALUES (%s, %s, %s, FROM_UNIXTIME(%s), %s)
                        """,
                        (
                            group_chat.get("chat_id"),
                            member_id,
                            member_type,
                            member.get("join_time") or 0,
                            unionid,
                        ),
                    )
                    up_member += 1
            cursor = listing.get("next_cursor")
            if not cursor:
                break
    return {"groupchats": up_chat, "members": up_member}
