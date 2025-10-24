#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wecom_sync_extdetail.py
按增量策略将企业微信「获取外部联系人详情」结果回填 wecom_ops.ext_contact
- 读取 ext_contact.external_userid 列表（增量条件可配）
- 调用接口 /cgi-bin/externalcontact/get
- 映射更新 name/corp_full_name/position/gender/unionid
- 存储完整 detail_json、follow_json、ext_json
- QPS/限频/重试/断点续跑
"""

import os, sys, time, json, argparse, hashlib, pathlib, datetime as dt
import requests, mysql.connector
from mysql.connector import errorcode
from dotenv import load_dotenv

SESSION = requests.Session()
SESSION_TIMEOUT = 10

def load_env():
    for p in ["/www/wwwroot/wecom_ops/.env", "./.env"]:
        if os.path.isfile(p):
            load_dotenv(p, override=False)

    corp_id = os.getenv("WX_CORP_ID") or os.getenv("WECOM_CORP_ID")
    # 优先客户联系，其次自建应用；允许显式强制偏好 Agent
    prefer_agent = os.getenv("WECOM_PREFER_AGENT", "").strip() in ("1", "true", "yes")

    cfg = dict(
        corp_id=corp_id,
        prefer_agent=prefer_agent,
        secret_contact=(os.getenv("WX_CONTACT_SECRET")
                        or os.getenv("WX_CUSTOMER_CONTACT_SECRET")
                        or os.getenv("WECOM_CONTACT_SECRET")),
        secret_agent=os.getenv("WECOM_AGENT_SECRET"),
        db_host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        db_port=int(os.getenv("MYSQL_PORT", "3306")),
        db_user=os.getenv("MYSQL_USER", "root"),
        db_pass=os.getenv("MYSQL_PASSWORD", ""),
        db_name=os.getenv("MYSQL_DB", "wecom_ops"),
    )
    if not cfg["corp_id"]:
        raise SystemExit("缺少 WX_CORP_ID（或 WECOM_CORP_ID）")
    if not (cfg["secret_contact"] or cfg["secret_agent"]):
        raise SystemExit("缺少可用的 Secret：请配置 WX_CONTACT_SECRET 或 WECOM_AGENT_SECRET")
    return cfg

# ----------- Access Token 缓存 -----------
def token_cache_path():
    return "/tmp/wecom_contact_token.json"

def get_access_token(corp_id, secret):
    cache_file = token_cache_path()
    now = int(time.time())
    if os.path.isfile(cache_file):
        try:
            data = json.load(open(cache_file, "r", encoding="utf-8"))
            if data.get("expire_at", 0) > now + 60 and data.get("corp_id")==corp_id and data.get("secret")==secret:
                return data["access_token"]
        except Exception:
            pass
    url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corp_id}&corpsecret={secret}"
    r = SESSION.get(url, timeout=SESSION_TIMEOUT)
    r.raise_for_status()
    j = r.json()
    if j.get("errcode") != 0:
        raise RuntimeError(f"gettoken err: {j}")
    access_token = j["access_token"]
    # 默认7200秒
    expire_at = now + int(j.get("expires_in", 7200)) - 60
    json.dump({"corp_id": corp_id, "secret": secret, "access_token": access_token, "expire_at": expire_at},
              open(cache_file, "w", encoding="utf-8"))
    return access_token

def has_contact_api_permission(access_token: str) -> bool:
    """探针：调用 get_follow_user_list，errcode 0 表示具备客户联系 API 权限；48002 表示无权限"""
    url = f"https://qyapi.weixin.qq.com/cgi-bin/externalcontact/get_follow_user_list?access_token={access_token}"
    try:
        r = SESSION.get(url, timeout=SESSION_TIMEOUT)
        r.raise_for_status()
        j = r.json()
        if j.get("errcode") == 0:
            return True
        if j.get("errcode") == 48002:
            return False
        # 其他错误（网络/临时）按无权限处理，但打印出来
        print(json.dumps({"probe_err": j}, ensure_ascii=False))
        return False
    except Exception as e:
        print(json.dumps({"probe_http_err": str(e)}))
        return False

# ----------- DB -----------
def get_db(cfg):
    return mysql.connector.connect(
        host=cfg["db_host"], port=cfg["db_port"],
        user=cfg["db_user"], password=cfg["db_pass"], database=cfg["db_name"],
        charset="utf8mb4", autocommit=True
    )

# ----------- 业务逻辑 -----------
def pick_targets(conn, days, limit, where_sql):
    """
    days: 多少天前更新过期（默认7天），NULL表示不过期条件
    limit: 限制数量（0=不限制）
    where_sql: 额外 WHERE 片段（安全起见仅供管理员使用）
    """
    cur = conn.cursor(dictionary=True)
    cond = ["external_userid IS NOT NULL", "external_userid<>''"]
    if days is not None:
        cond.append(f"(detail_json IS NULL OR updated_at < NOW() - INTERVAL {int(days)} DAY)")
    if where_sql:
        cond.append(f"({where_sql})")
    sql = f"SELECT external_userid FROM ext_contact WHERE {' AND '.join(cond)} ORDER BY updated_at ASC"
    if limit and int(limit) > 0:
        sql += f" LIMIT {int(limit)}"
    cur.execute(sql)
    rows = [r["external_userid"] for r in cur.fetchall()]
    cur.close()
    return rows

def fetch_detail(access_token, external_userid):
    url = "https://qyapi.weixin.qq.com/cgi-bin/externalcontact/get"
    all_follow = []
    base = None
    cursor = None
    while True:
        params = {"access_token": access_token, "external_userid": external_userid}
        if cursor:
            params["cursor"] = cursor
        r = SESSION.get(url, params=params, timeout=SESSION_TIMEOUT)
        r.raise_for_status()
        j = r.json()
        if j.get("errcode") != 0:
            return None, j
        if base is None:
            base = j  # 保存第一包，包含 external_contact
        fu = j.get("follow_user") or []
        if fu:
            all_follow.extend(fu)
        cursor = j.get("next_cursor")
        if not cursor:
            break
    if base is None:
        return None, {"errcode": -1, "errmsg": "empty response"}
    base["follow_user"] = all_follow  # 合并所有页
    base.pop("next_cursor", None)
    return base, None

def normalize_for_columns(j):
    """
    从接口返回体提取：name, corp_full_name, position, gender, unionid
    同时拆 follow_json / ext_json
    """
    ext = (j or {}).get("external_contact") or {}
    name = ext.get("name") or None
    corp_full_name = ext.get("corp_full_name") or ext.get("corp_name") or None
    position = ext.get("position") or None
    gender = ext.get("gender") or None
    unionid = ext.get("unionid") or None

    follow_json = j.get("follow_user") or j.get("follow_user_list") or []  # 不同版本字段名兼容
    # 自定义属性通常在 external_profile / external_attr
    ext_json = {
        "external_profile": ext.get("external_profile"),
        "external_attr": ext.get("external_attr"),
    }
    return name, corp_full_name, position, gender, unionid, follow_json, ext_json

def upsert_detail(conn, external_userid, j):
    name, corp_full_name, position, gender, unionid, follow_json, ext_json = normalize_for_columns(j)
    detail_json_str = json.dumps(j, ensure_ascii=False)
    follow_json_str = json.dumps(follow_json, ensure_ascii=False)
    ext_json_str = json.dumps(ext_json, ensure_ascii=False)

    sql = """
    INSERT INTO ext_contact (
        external_userid, name, corp_full_name, position, gender, unionid,
        detail_json, follow_json, ext_json, updated_at
    ) VALUES (
        %(external_userid)s, %(name)s, %(corp_full_name)s, %(position)s, %(gender)s, %(unionid)s,
        %(detail_json)s, %(follow_json)s, %(ext_json)s, NOW()
    )
    ON DUPLICATE KEY UPDATE
        name = COALESCE(%(name)s, name),
        corp_full_name = COALESCE(%(corp_full_name)s, corp_full_name),
        position = COALESCE(%(position)s, position),
        gender = COALESCE(%(gender)s, gender),
        unionid = COALESCE(NULLIF(%(unionid)s, ''), unionid),
        detail_json = %(detail_json)s,
        follow_json = %(follow_json)s,
        ext_json = %(ext_json)s,
        updated_at = NOW()
    """
    cur = conn.cursor()
    cur.execute(sql, {
        "external_userid": external_userid,
        "name": name,
        "corp_full_name": corp_full_name,
        "position": position,
        "gender": gender,
        "unionid": unionid,
        "detail_json": detail_json_str,
        "follow_json": follow_json_str,
        "ext_json": ext_json_str,
    })
    cur.close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7, help="更新阈值天数：detail_json 为空或超过 N 天未更新即回填；设为 -1 表示不过期条件")
    ap.add_argument("--limit", type=int, default=0, help="最多处理条数（0=不限）")
    ap.add_argument("--qps", type=float, default=6.0, help="最大 QPS（建议 ≤6）")
    ap.add_argument("--where-sql", default="", help="附加 WHERE 条件（仅管理员使用）")
    args = ap.parse_args()

    cfg = load_env()
    conn = get_db(cfg)

    days = None if args.days is not None and args.days < 0 else args.days
    targets = pick_targets(conn, days=days, limit=args.limit, where_sql=args.where_sql)
    if not targets:
        print(json.dumps({"ok": True, "scanned": 0, "updated": 0, "note": "no targets"}))
        return

        # 选择 Secret：优先策略 or 探针回退
    token = None
    used = None
    if cfg["prefer_agent"] and cfg["secret_agent"]:
        token = get_access_token(cfg["corp_id"], cfg["secret_agent"])
        used = "agent"
    else:
        # 先尝试 contact，再探针回退
        if cfg["secret_contact"]:
            t1 = get_access_token(cfg["corp_id"], cfg["secret_contact"])
            if has_contact_api_permission(t1):
                token, used = t1, "contact"
            elif cfg["secret_agent"]:
                t2 = get_access_token(cfg["corp_id"], cfg["secret_agent"])
                if has_contact_api_permission(t2):
                    token, used = t2, "agent"
        elif cfg["secret_agent"]:
            t2 = get_access_token(cfg["corp_id"], cfg["secret_agent"])
            if has_contact_api_permission(t2):
                token, used = t2, "agent"

    if not token:
        raise SystemExit("无法获得具备客户联系权限的 access_token，请检查后台『客户联系·可调用接口的应用』与应用可见范围。")
    else:
        print(json.dumps({"using_secret": used}, ensure_ascii=False))
    per_sleep = 1.0 / max(0.1, args.qps)

    ok, fail = 0, 0
    for i, extuid in enumerate(targets, 1):
        t0 = time.time()
        try:
            j, err = fetch_detail(token, extuid)
            if err:
                fail += 1
                print(json.dumps({"ext_uid": extuid, "err": err}, ensure_ascii=False))
            else:
                upsert_detail(conn, extuid, j)
                ok += 1
        except requests.HTTPError as e:
            fail += 1
            print(json.dumps({"ext_uid": extuid, "http_error": str(e)}))
        except Exception as e:
            fail += 1
            print(json.dumps({"ext_uid": extuid, "error": str(e)}))

        # 控制 QPS
        used = time.time() - t0
        if used < per_sleep:
            time.sleep(per_sleep - used)

        if i % 50 == 0:
            print(json.dumps({"progress": f"{i}/{len(targets)}", "ok": ok, "fail": fail}, ensure_ascii=False))

    print(json.dumps({"ok": True, "scanned": len(targets), "updated": ok, "failed": fail}, ensure_ascii=False))

if __name__ == "__main__":
    main()