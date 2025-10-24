#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, time, json, argparse, requests, pymysql

QY = "https://qyapi.weixin.qq.com"

def env(name, default=None, required=False):
    v = os.getenv(name, default)
    if required and not v:
        raise RuntimeError(f"missing env {name}")
    return v

def get_token():
    corp = env("WECOM_CORP_ID", required=True)
    sec  = env("WECOM_EXT_SECRET") or env("WECOM_AGENT_SECRET")
    if not sec:
        raise RuntimeError("missing WECOM_EXT_SECRET / WECOM_AGENT_SECRET")
    r = requests.get(f"{QY}/cgi-bin/gettoken", params={"corpid": corp, "corpsecret": sec}, timeout=10)
    r.raise_for_status()
    data = r.json()
    if data.get("errcode") != 0:
        raise RuntimeError(f"gettoken error: {data}")
    return data["access_token"]

def sql_conn():
    return pymysql.connect(
        host=env("MYSQL_HOST","127.0.0.1"),
        port=int(env("MYSQL_PORT","3306")),
        user=env("MYSQL_USER", required=True),
        password=env("MYSQL_PASSWORD", required=True),
        database=env("MYSQL_DB", required=True),
        charset="utf8mb4", autocommit=True,
        cursorclass=pymysql.cursors.DictCursor
    )

def ensure_tables(cur):
    cur.execute("""
      CREATE TABLE IF NOT EXISTS ext_contact_tag (
        external_userid VARCHAR(64) NOT NULL,
        tag_id          VARCHAR(64) NOT NULL,
        owner_userid    VARCHAR(64) NOT NULL,
        updated_at      TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (external_userid, tag_id, owner_userid)
      ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;""")

def fetch_follow_users(cur, only_active=True):
    if only_active:
        cur.execute("SELECT userid FROM ext_follow_user WHERE status IN (1,2)")
    else:
        cur.execute("SELECT userid FROM ext_follow_user")
    return [r["userid"] for r in cur.fetchall()]

def list_external_userids(at, userid):
    r = requests.get(f"{QY}/cgi-bin/externalcontact/list",
                     params={"access_token": at, "userid": userid}, timeout=15)
    data = r.json()
    if data.get("errcode") == 0:
        return data.get("external_userid", [])
    # 84061: 非客户或无权限 -> 跳过该跟进人
    if data.get("errcode") in (84061, 48001, 48009):
        return []
    raise RuntimeError(f"list error for {userid}: {data}")

# 外部联系人详情返回的标签键为 tag_id
def get_contact_detail(at, external_userid):
    r = requests.get(f"{QY}/cgi-bin/externalcontact/get",
                     params={"access_token": at, "external_userid": external_userid}, timeout=20)
    return r.json()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=1000)
    ap.add_argument("--start-after", dest="start_after", default=None)
    ap.add_argument("--sleep", type=float, default=0.05, help="每次详情请求之间的sleep秒数")
    ap.add_argument("--all-users", action="store_true", help="包含非在职/禁用的跟进人")
    args = ap.parse_args()

    at = get_token()
    conn = sql_conn()
    cur  = conn.cursor()
    ensure_tables(cur)

    # 读取待处理的 external_userid（仅处理 unionid 为空的）
    where = ""
    params = []
    if args.start_after:
        where = "AND external_userid > %s"
        params.append(args.start_after)

    sql = f"""
      SELECT external_userid
      FROM ext_contact
      WHERE (unionid IS NULL OR unionid = '')
      {where}
      ORDER BY external_userid
      LIMIT %s
    """
    params.append(args.limit)

    cur.execute(sql, params)
    rows = cur.fetchall()
    ext_ids_list = [row["external_userid"] for row in rows]

    userids = fetch_follow_users(cur, only_active=(not args.all_users))

    done_ctags = 0
    scanned_contacts = 0

    ins_sql = """INSERT INTO ext_contact_tag (external_userid, tag_id, owner_userid)
                 VALUES (%s,%s,%s)
                 ON DUPLICATE KEY UPDATE owner_userid=VALUES(owner_userid)"""

    for eid in ext_ids_list:
        detail = get_contact_detail(at, eid)
        if detail.get("errcode") != 0:
            # 常见：84061 某些外部联系人不再可见，忽略
            time.sleep(args.sleep)
            continue
        
        # 补写回 unionid（仅空时更新）
        ext = detail.get("external_contact") or {}
        unionid = ext.get("unionid") or ""
        if unionid:
            cur.execute(
                "UPDATE ext_contact SET unionid=%s "
                "WHERE external_userid=%s AND (unionid IS NULL OR unionid='')",
                (unionid, eid)
            )
            # 维护身份映射
            cur.execute("""
              INSERT INTO user_union_info (mobile, unionid, external_userid, source, last_seen_at)
              VALUES ('', %s, %s, 'wecom_ext_contact', NOW())
              ON DUPLICATE KEY UPDATE external_userid=VALUES(external_userid), last_seen_at=NOW()
            """, (unionid, eid))
        
        # 原有标签处理逻辑
        for fu in detail.get("follow_user", []) or []:
            uid = fu.get("userid")
            if uid not in userids:
                continue
                
            for tg in fu.get("tags", []) or []:
                # 兼容不同返回结构，尝试多种可能的键名
                tid = tg.get("id") or tg.get("tag_id") or tg.get("tagid")
                if not tid:
                    continue  # 防止插入 NULL
                cur.execute(ins_sql, (eid, tid, uid))
                done_ctags += 1
        
        scanned_contacts += 1
        time.sleep(args.sleep)

    last_eid = rows[-1]["external_userid"] if rows else None
    print(json.dumps({
        "ok": True,
        "scanned": scanned_contacts,
        "inserted_or_updated": done_ctags,
        "last_external_userid": last_eid
    }, ensure_ascii=False))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        raise