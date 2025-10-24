#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, time, json, math, argparse
import requests, mysql.connector
from mysql.connector import errorcode

def get_db():
    cfg = dict(
        host=os.getenv("MYSQL_HOST","127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT","3306")),
        user=os.getenv("MYSQL_USER","wecom_ops"),
        password=os.getenv("MYSQL_PASSWORD",""),
        database=os.getenv("MYSQL_DB","wecom_ops"),
        charset=os.getenv("MYSQL_CHARSET","utf8mb4"),
    )
    return mysql.connector.connect(**cfg)

def get_token():
    corp = os.getenv("WX_CORP_ID") or os.getenv("WECOM_CORP_ID")
    sec  = os.getenv("WECOM_AGENT_SECRET")  # 自建应用
    r = requests.get("https://qyapi.weixin.qq.com/cgi-bin/gettoken",
                     params={"corpid":corp,"corpsecret":sec}, timeout=15).json()
    if r.get("errcode")!=0:
        raise RuntimeError(f"gettoken failed: {r}")
    return r["access_token"]

def probe_follow_users(access_token: str) -> list[str]:
    """
    调用 get_follow_user_list 获取已开通客户联系的员工 userid 列表。
    - 明确检查 errcode != 0 的情况（常见：48002 api forbidden）
    - 兜底做类型检查，避免把字符串当列表迭代
    """
    import requests
    url = "https://qyapi.weixin.qq.com/cgi-bin/externalcontact/get_follow_user_list"
    r = requests.get(url, params={"access_token": access_token}, timeout=15)
    try:
        j = r.json()
    except Exception:
        raise RuntimeError(f"get_follow_user_list non-json response: {r.status_code} {r.text[:200]}")

    ec = j.get("errcode", -1)
    if ec != 0:
        # 48002 大概率是自建应用权限或可见范围不含“客户联系”
        raise RuntimeError(f"get_follow_user_list failed: errcode={ec}, errmsg={j.get('errmsg')}, body={j}")

    fu = j.get("follow_user", [])
    if isinstance(fu, dict):
        # 极端情况：单对象
        fu = [fu]
    if not isinstance(fu, list):
        raise RuntimeError(f"unexpected follow_user type: {type(fu).__name__} value={fu}")

    userids = [u.get("userid") for u in fu if isinstance(u, dict) and u.get("userid")]
    if not userids:
        # API 成功但没有任何开通客户联系的成员
        raise RuntimeError("no follow_user returned (nobody has enabled Customer Contact?)")
    return userids

def load_userids_from_db(limit_users=0):
    """从 ext_contact.owner_userid 去重取 userid"""
    sql = "SELECT owner_userid FROM ext_contact WHERE owner_userid IS NOT NULL GROUP BY owner_userid"
    if limit_users and limit_users > 0:
        sql += f" LIMIT {int(limit_users)}"
    cn = get_db(); cur = cn.cursor()
    cur.execute(sql); rows = [r[0] for r in cur.fetchall()]
    cur.close(); cn.close()
    return rows

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]

def upsert_contact_and_tags(cn, ec, fi):
    """回写 ext_contact / ext_contact_tag（用单条 upsert + 覆盖标签）"""
    external_userid = ec.get("external_userid")
    unionid  = ec.get("unionid")
    name     = ec.get("name")
    corp_name= ec.get("corp_full_name") or ec.get("corp_name")
    owner    = (fi or {}).get("userid")

    detail_json = json.dumps(ec, ensure_ascii=False)

    cur = cn.cursor()

    # ext_contact upsert（确保 is_deleted 置 0）
    cur.execute("""
    INSERT INTO ext_contact (external_userid, unionid, name, corp_name, owner_userid, detail_json, updated_at, is_deleted)
    VALUES (%s,%s,%s,%s,%s,%s,NOW(),0)
    ON DUPLICATE KEY UPDATE
      unionid=VALUES(unionid),
      name=VALUES(name),
      corp_name=VALUES(corp_name),
      owner_userid=COALESCE(VALUES(owner_userid), owner_userid),
      detail_json=VALUES(detail_json),
      updated_at=NOW(),
      is_deleted=0
    """, (external_userid, unionid, name, corp_name, owner, detail_json))

    # 标签：本次结果里的 tag_id 代表“当前集合”，我们做覆盖
    tag_ids = (fi or {}).get("tag_id") or []
    cur.execute("DELETE FROM ext_contact_tag WHERE external_userid=%s", (external_userid,))
    if tag_ids:
        cur.executemany("""
          INSERT INTO ext_contact_tag (external_userid, tag_id, tag_name, group_name, created_at, updated_at)
          VALUES (%s,%s,NULL,NULL,NOW(),NOW())
        """, [(external_userid, t) for t in tag_ids])

    cur.close()

def run(limit_users=0, qps=4, per_batch=100, dry_run=False, source="auto"):
    token = get_token()

    # 取 userid_list
    userids = []
    if source in ("auto","api"):
        userids = probe_follow_users(token)
    if not userids and source in ("auto","db"):
        userids = load_userids_from_db(limit_users)
    if not userids:
        print(json.dumps({"ok": True, "note": "no userids to scan"})); return

    cn = get_db()
    scanned_users = 0
    upserts = 0

    for us in chunks(userids, per_batch):
        payload = {"userid_list": us[:100], "limit": 100}
        cursor = ""
        while True:
            if cursor:
                payload["cursor"] = cursor
            r = requests.post(
                "https://qyapi.weixin.qq.com/cgi-bin/externalcontact/batch/get_by_user",
                params={"access_token":token},
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                timeout=30
            ).json()

            if r.get("errcode") == 701008:
                # 这些 userid 无互通许可，跳过
                break
            if r.get("errcode") != 0:
                raise RuntimeError(f"batch/get_by_user failed: {r}")

            lst = r.get("external_contact_list") or []
            if not dry_run:
                for item in lst:
                    ec = item.get("external_contact") or {}
                    fi = item.get("follow_info") or {}
                    upsert_contact_and_tags(cn, ec, fi)
                cn.commit()
                upserts += len(lst)

            cursor = r.get("next_cursor") or ""
            if not cursor:
                break

            time.sleep(1.0 / max(1, qps))

        scanned_users += len(us)

    cn.close()
    print(json.dumps({"ok": True, "scanned_users": scanned_users, "upserts": upserts}))
    return

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit-users", type=int, default=0, help="仅取前 N 个 userid（0=不限）")
    ap.add_argument("--qps", type=float, default=4.0, help="批量接口限速")
    ap.add_argument("--per-batch", type=int, default=100, help="一次请求的 userid 数量（<=100）")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--source", default="auto", choices=["auto","api","db"], help="userid 来源优先级")
    args = ap.parse_args()
    run(limit_users=args.limit_users, qps=args.qps, per_batch=args.per_batch, dry_run=args.dry_run, source=args.source)