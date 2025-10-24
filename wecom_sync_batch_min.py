#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, time, json, math, argparse, requests, mysql.connector as mc
from datetime import datetime as dt

def env(name, default=None):
    v = os.getenv(name, default)
    if v is None or (isinstance(v,str) and not v.strip()):
        return default
    return v

def get_token():
    corp = env("WX_CORP_ID") or env("WECOM_CORP_ID")
    # 用自建应用的 Agent Secret（你已验证可返回跟进人列表）
    sec  = env("WECOM_AGENT_SECRET")
    r = requests.get("https://qyapi.weixin.qq.com/cgi-bin/gettoken",
                     params={"corpid":corp,"corpsecret":sec}, timeout=15).json()
    if r.get("errcode") != 0:
        raise RuntimeError(f"gettoken failed: {r}")
    return r["access_token"]

def get_follow_users(token):
    r = requests.get("https://qyapi.weixin.qq.com/cgi-bin/externalcontact/get_follow_user_list",
                     params={"access_token":token}, timeout=30).json()
    if r.get("errcode") != 0:
        raise RuntimeError(f"get_follow_user_list failed: {r}")
    fu = r.get("follow_user", [])
    # 兼容 list[str] 与 list[dict]
    if fu and isinstance(fu[0], dict):
        return [u.get("userid") for u in fu if u.get("userid")]
    return list(fu)

def get_tag_map(token):
    # 拉企业标签映射（id -> (name, group_name)）
    r = requests.post(
        "https://qyapi.weixin.qq.com/cgi-bin/externalcontact/get_corp_tag_list",
        params={"access_token":token}, json={}, timeout=30
    ).json()
    if r.get("errcode") != 0:
        # 没权限也不阻塞主流程，后面写 tag_name=None
        return {}
    m = {}
    for g in r.get("tag_group", []):
        gname = g.get("group_name")
        for t in g.get("tag", []):
            m[t["id"]] = (t.get("name"), gname)
    return m

def get_conn():
    return mc.connect(
        host=env("MYSQL_HOST","127.0.0.1"),
        port=int(env("MYSQL_PORT","3306")),
        user=env("MYSQL_USER"),
        password=env("MYSQL_PASSWORD"),
        database=env("MYSQL_DB","wecom_ops"),
        charset="utf8mb4"
    )

def chunked(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i+n]

def batch_get_by_user(token, userids, per_batch=100, qps=3.0):
    # 按 100 个 userid 一组调用；对每组用 next_cursor 翻页
    for group in chunked(userids, per_batch):
        cursor = ""
        while True:
            payload = {"userid_list": group, "limit": 100}
            if cursor:
                payload["cursor"] = cursor
            r = requests.post(
                "https://qyapi.weixin.qq.com/cgi-bin/externalcontact/batch/get_by_user",
                params={"access_token":token},
                json=payload, timeout=60
            ).json()
            if r.get("errcode") != 0:
                # 如果全部 userid 都没互通许可会报 701008；仅记录并继续下一组
                print(json.dumps({"when":"batch", "group":group, "resp":r}, ensure_ascii=False))
                break
            for rec in r.get("external_contact_list", []):
                yield rec
            cursor = r.get("next_cursor") or ""
            if not cursor:
                break
            time.sleep(1.0/max(qps,0.1))
        time.sleep(1.0/max(qps,0.1))

def upsert_contact(cur, ec):
    # 仅用到稳定字段；detail_json 存 external_contact 原文
    ext_id = ec.get("external_userid")
    if not ext_id:
        return
    unionid = ec.get("unionid")
    name    = ec.get("name")
    corp    = ec.get("corp_name")
    corpfull= ec.get("corp_full_name")
    position= ec.get("position")
    gender  = ec.get("gender")
    detail  = json.dumps(ec, ensure_ascii=False)
    cur.execute("""
    INSERT INTO ext_contact
      (external_userid, unionid, name, corp_name, corp_full_name, position, gender, detail_json, is_deleted, updated_at)
    VALUES (%(eid)s, %(unionid)s, %(name)s, %(corp)s, %(corpfull)s, %(position)s, %(gender)s, %(detail)s, 0, NOW())
    ON DUPLICATE KEY UPDATE
      unionid=VALUES(unionid),
      name=VALUES(name),
      corp_name=VALUES(corp_name),
      corp_full_name=VALUES(corp_full_name),
      position=VALUES(position),
      gender=VALUES(gender),
      detail_json=VALUES(detail_json),
      is_deleted=0,
      updated_at=NOW()
    """, dict(eid=ext_id, unionid=unionid, name=name, corp=corp, corpfull=corpfull,
              position=position, gender=gender, detail=detail))

def upsert_tags(cur, ext_id, tag_ids, tag_map):
    if not tag_ids:
        return
    vals = []
    for tid in set(tag_ids):
        tname, gname = (tag_map.get(tid) or (None, None))
        vals.append((ext_id, tid, tname, gname))
    cur.executemany("""
    INSERT IGNORE INTO ext_contact_tag (external_userid, tag_id, tag_name, group_name)
    VALUES (%s,%s,%s,%s)
    """, vals)

def main(limit_users=10, per_batch=100, qps=3.0):
    tok = get_token()
    userids = get_follow_users(tok)
    if not userids:
        print(json.dumps({"ok": False, "error": "no_follow_user"}))
        return
    userids = userids[:limit_users] if limit_users>0 else userids
    tag_map = get_tag_map(tok)

    conn = get_conn(); conn.autocommit = False
    cur = conn.cursor()
    scanned = updated = 0
    try:
        for rec in batch_get_by_user(tok, userids, per_batch=per_batch, qps=qps):
            ec = rec.get("external_contact") or {}
            fi = rec.get("follow_info") or {}
            ext_id = (ec.get("external_userid") or fi.get("external_userid"))
            if not ext_id:
                continue
            upsert_contact(cur, ec)
            upsert_tags(cur, ext_id, fi.get("tag_id") or [], tag_map)
            scanned += 1; updated += 1
            if scanned % 500 == 0:
                conn.commit()
        conn.commit()
        print(json.dumps({"ok": True, "scanned": scanned, "updated": updated}))
    finally:
        try: cur.close()
        except: pass
        try: conn.close()
        except: pass

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit-users", type=int, default=10, help="仅取前 N 个跟进人做验证；<=0 表示全部")
    ap.add_argument("--per-batch", type=int, default=100, help="每次 userid_list 的规模（<=100）")
    ap.add_argument("--qps", type=float, default=3.0, help="节流 QPS（粗略控制）")
    args = ap.parse_args()
    main(limit_users=args.limit_users, per_batch=max(1,min(100,args.per_batch)), qps=max(0.1,args.qps))
