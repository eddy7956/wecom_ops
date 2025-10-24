# -*- coding: utf-8 -*-
import os, pymysql
from app.wecom.client import wecom_post_json

def _db():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST","127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT","3306")),
        user=os.getenv("MYSQL_USER","root"),
        password=os.getenv("MYSQL_PASSWORD",""),
        database=os.getenv("MYSQL_DB"),
        charset="utf8mb4",
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor)

def sync_groupchats(limit=100):
    cursor = None; up_chat = up_mem = 0
    with _db().cursor() as c:
        while True:
            body = {"status_filter": 0, "owner_filter": {}, "cursor": cursor, "limit": limit}
            lst = wecom_post_json("https://qyapi.weixin.qq.com/cgi-bin/externalcontact/groupchat/list",
                                  "ext", body=body)
            for item in lst.get("group_chat_list", []):
                chat_id = item.get("chat_id")
                detail = wecom_post_json("https://qyapi.weixin.qq.com/cgi-bin/externalcontact/groupchat/get",
                                         "ext", body={"chat_id": chat_id})
                gc = detail.get("group_chat", {})
                c.execute("""REPLACE INTO ec_groupchat
                             (chat_id,name,owner,notice,create_time,status,ext)
                             VALUES (%s,%s,%s,%s,FROM_UNIXTIME(%s),%s,%s)""",
                          (gc.get("chat_id"), gc.get("name"), gc.get("owner"),
                           gc.get("notice"), gc.get("create_time") or 0,
                           gc.get("status"), None))
                up_chat += 1
                for m in gc.get("member_list", []):
                    if m.get("type") == 1:
                        mid, mtype, unionid = m.get("userid"), "employee", None
                    else:
                        mid, mtype, unionid = m.get("external_userid"), "external", m.get("unionid")
                    c.execute("""REPLACE INTO ec_groupchat_member
                                 (chat_id, member_id, member_type, join_time, unionid)
                                 VALUES (%s,%s,%s,FROM_UNIXTIME(%s),%s)""",
                              (gc.get("chat_id"), mid, mtype, m.get("join_time") or 0, unionid))
                    up_mem += 1
            cursor = lst.get("next_cursor")
            if not cursor: break
    return {"groupchats": up_chat, "members": up_mem}
