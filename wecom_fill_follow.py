#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, time, json, math, argparse, datetime as dt
import requests, mysql.connector
from mysql.connector import errorcode
from dotenv import load_dotenv

load_dotenv("/www/wwwroot/wecom_ops/.env")

DB = dict(
    host=os.getenv("MYSQL_HOST","127.0.0.1"),
    port=int(os.getenv("MYSQL_PORT","3306") or 3306),
    user=os.getenv("MYSQL_USER","wecom_ops"),
    password=os.getenv("MYSQL_PASSWORD",""),
    database=os.getenv("MYSQL_DB","wecom_ops"),
    charset=os.getenv("MYSQL_CHARSET","utf8mb4"),
)

CORP = os.getenv("WX_CORP_ID") or os.getenv("WECOM_CORP_ID")
SEC  = (os.getenv("WECOM_AGENT_SECRET") or os.getenv("WECOM_CONTACT_SECRET")
        or os.getenv("WECOM_CONTACTS_SECRET") or os.getenv("WECOM_EXT_SECRET"))

SESSION = requests.Session()
SESSION_TIMEOUT=20

def get_token():
    r = SESSION.get("https://qyapi.weixin.qq.com/cgi-bin/gettoken",
        params={"corpid": CORP, "corpsecret": SEC}, timeout=SESSION_TIMEOUT).json()
    if r.get("errcode") != 0:
        raise RuntimeError(f"gettoken failed: {r}")
    return r["access_token"]

def get_follow_users(token):
    r = SESSION.get("https://qyapi.weixin.qq.com/cgi-bin/externalcontact/get_follow_user_list",
        params={"access_token": token}, timeout=SESSION_TIMEOUT).json()
    if r.get("errcode") != 0:
        raise RuntimeError(f"get_follow_user_list failed: {r}")
    # 文档与实测都可能返回数组或对象列表，统一成纯字符串 userid 列表
    users = r.get("follow_user") or []
    if users and isinstance(users[0], dict):
        users = [u.get("userid") for u in users if u.get("userid")]
    return [u for u in users if u]

def chunk(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]

def upsert_follow_rows(cur, rows):
    # rows: [(ext_id, userid, first_follow_at)]
    if not rows: return
    cur.executemany("""
        INSERT IGNORE INTO ext_contact_follow (external_userid, userid, first_follow_at, created_at, updated_at)
        VALUES (%s, %s, %s, NOW(), NOW())
    """, rows)

def recalc_is_unassigned(cur):
    cur.execute("""
        UPDATE ext_contact e
        LEFT JOIN (SELECT DISTINCT external_userid FROM ext_contact_follow) f
          ON f.external_userid = e.external_userid
        SET e.is_unassigned = CASE WHEN f.external_userid IS NULL THEN 1 ELSE 0 END,
            e.updated_at = NOW()
        WHERE COALESCE(e.is_deleted,0)=0
    """)

def sync_unassigned_pool(cur):
    # 失活：已有跟进的待分配
    cur.execute("""
        UPDATE ext_unassigned un
        JOIN ext_contact_follow f ON f.external_userid=un.external_userid
        SET un.is_active=0,
            un.reason=COALESCE(NULLIF(un.reason,''),'follow_backfill'),
            un.updated_at=NOW()
        WHERE un.is_active=1
    """)
    # 补入：仍无人跟进的
    cur.execute("""
        INSERT IGNORE INTO ext_unassigned (external_userid,is_active,reason,created_at,updated_at)
        SELECT e.external_userid,1,'recalc',NOW(),NOW()
        FROM ext_contact e
        LEFT JOIN ext_contact_follow f ON f.external_userid=e.external_userid
        LEFT JOIN ext_unassigned un ON un.external_userid=e.external_userid AND un.is_active=1
        WHERE COALESCE(e.is_deleted,0)=0
        GROUP BY e.external_userid
        HAVING COALESCE(COUNT(f.userid),0)=0 AND MAX(COALESCE(un.is_active,0))=0
    """)

def batch_get_by_user(token, userid_list, qps=3.0):
    url="https://qyapi.weixin.qq.com/cgi-bin/externalcontact/batch/get_by_user"
    cursor = None
    while True:
        body={"userid_list": userid_list, "limit": 100}
        if cursor: body["cursor"]=cursor
        r = SESSION.post(url, params={"access_token":token}, json=body, timeout=SESSION_TIMEOUT).json()
        if r.get("errcode") != 0:
            raise RuntimeError(f"batch/get_by_user failed: {r}")
        yield r
        cursor = r.get("next_cursor")
        if not cursor: break
        time.sleep(1.0/max(0.1,qps))

def main(limit_users=0, per_batch=50, qps=3.0, dry_run=False):
    token = get_token()
    users = get_follow_users(token)
    if limit_users>0: users = users[:limit_users]
    if not users:
        print(json.dumps({"ok":True,"note":"no follow users"})); return

    cnx = mysql.connector.connect(**DB)
    cur = cnx.cursor()

    total_rows = 0
    for group in chunk(users, per_batch):
        # 拉批详情
        rows=[]
        for r in batch_get_by_user(token, group, qps=qps):
            for item in r.get("external_contact_list", []):
                ext = item.get("external_contact") or {}
                ext_id = ext.get("external_userid")
                fi = item.get("follow_info") or {}
                # 注意：接口返回是“一客一跟进人”的列表；当同一 external_userid 归属于多个导购时，会返回多条 item
                userid = fi.get("userid")
                t = fi.get("createtime")
                first_at = None
                if isinstance(t, int) and t>0:
                    first_at = dt.datetime.fromtimestamp(t)
                if ext_id and userid:
                    rows.append((ext_id, userid, first_at))

        if rows and not dry_run:
            upsert_follow_rows(cur, rows)
            recalc_is_unassigned(cur)
            sync_unassigned_pool(cur)
            cnx.commit()
            total_rows += len(rows)

        time.sleep(1.0/max(0.1,qps))

    cur.close(); cnx.close()
    print(json.dumps({"ok":True, "inserted": total_rows, "users_scanned": len(users)}))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit-users", type=int, default=0, help="只处理前 N 个导购（0 表示全部）")
    ap.add_argument("--per-batch", type=int, default=50, help="userid 批量大小（<=100）")
    ap.add_argument("--qps", type=float, default=3.0, help="请求限速（每秒请求数）")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    main(limit_users=args.limit_users, per_batch=max(1,min(100,args.per_batch)), qps=max(0.1,args.qps), dry_run=args.dry_run)
