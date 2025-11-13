# -*- coding: utf-8 -*-
"""客服同步相关服务。"""

from app.core.db import get_mysql_conn
from app.wecom.client import wecom_get_json


@contextmanager
def _use_cursor():
    """提供一次性游标，确保数据库连接按需释放。"""
    conn = get_mysql_conn()
    try:
        with conn.cursor() as cur:
            yield cur
    finally:
        try:
            conn.close()
        except Exception:
            pass


def sync_kf_accounts(offset: int = 0, limit: int = 100) -> dict:
    up = 0
    with _use_cursor() as cur:
        while True:
            data = wecom_get_json(
                "https://qyapi.weixin.qq.com/cgi-bin/kf/account/list",
                "kf",
                params={"offset": offset, "limit": limit},
            )
            for account in data.get("account_list", []):
                cur.execute(
                    """
                    REPLACE INTO kf_account (open_kfid, name, status, ext)
                    """,
                    (
                        account.get("open_kfid"),
                        account.get("name"),
                        account.get("status"),
                    ),
                )
                up += 1
            if len(data.get("account_list", [])) < limit:
                break
            offset += limit
    return {"kf_accounts": up}


def sync_kf_servicers() -> dict:
    up = 0
    with _use_cursor() as cur:
        cur.execute("SELECT open_kfid FROM kf_account")
        for row in cur.fetchall():
            kfid = row["open_kfid"]
            detail = wecom_get_json(
                "https://qyapi.weixin.qq.com/cgi-bin/kf/servicer/list",
                "kf",
                params={"open_kfid": kfid},
            )
            for user in detail.get("servicer_list", []):
                cur.execute(
                    """
                    REPLACE INTO kf_servicer (open_kfid, userid, status)
                    VALUES (%s, %s, %s)
                    """,
                    (kfid, user.get("userid"), 1),
                )
                up += 1
    return {"kf_servicers": up}
