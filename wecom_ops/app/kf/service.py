# -*- coding: utf-8 -*-
import os, pymysql
from app.wecom.client import wecom_get_json

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

def sync_kf_accounts(offset=0, limit=100):
    up = 0
    with _db().cursor() as c:
        while True:
            data = wecom_get_json("https://qyapi.weixin.qq.com/cgi-bin/kf/account/list","kf",
                                  params={"offset": offset, "limit": limit})
            for a in data.get("account_list", []):
                c.execute("""REPLACE INTO kf_account (open_kfid,name,status,ext)
                             VALUES (%s,%s,%s,JSON_OBJECT())""",
                          (a.get("open_kfid"), a.get("name"), a.get("status")))
                up += 1
            if len(data.get("account_list", [])) < limit:
                break
            offset += limit
    return {"kf_accounts": up}

def sync_kf_servicers():
    up = 0
    with _db().cursor() as c:
        c.execute("SELECT open_kfid FROM kf_account")
        for row in c.fetchall():
            kfid = row["open_kfid"]
            dt = wecom_get_json("https://qyapi.weixin.qq.com/cgi-bin/kf/servicer/list","kf",
                                params={"open_kfid": kfid})
            for u in dt.get("servicer_list", []):
                c.execute("""REPLACE INTO kf_servicer (open_kfid, userid, status)
                             VALUES (%s,%s,%s)""", (kfid, u.get("userid"), 1))
                up += 1
    return {"kf_servicers": up}
