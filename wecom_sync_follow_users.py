# -*- coding: utf-8 -*-
import os, json, requests, pymysql, sys

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

def main():
    at = get_token()
    r = requests.get(f"{QY}/cgi-bin/externalcontact/get_follow_user_list",
                     params={"access_token": at}, timeout=15)
    data = r.json()
    if data.get("errcode") != 0:
        raise RuntimeError(f"get_follow_user_list error: {data}")
    users = data.get("follow_user") or []

    conn = sql_conn()
    with conn.cursor() as cur:
        # 1) 读取现有集合
        cur.execute("SELECT userid FROM ext_follow_user")
        existing = {row["userid"] for row in cur.fetchall()}

        incoming = set(users)
        # 2) upsert 新用户
        if incoming:
            cur.executemany(
                "INSERT INTO ext_follow_user (userid) VALUES (%s) "
                "ON DUPLICATE KEY UPDATE userid=VALUES(userid)", [(u,) for u in incoming]
            )
        # 3) 删除已不在列表的用户（仅当 API 返回非空时才做）
        to_del = list(existing - incoming) if incoming else []
        if to_del:
            cur.executemany("DELETE FROM ext_follow_user WHERE userid=%s", [(u,) for u in to_del])

        # 4) 用 org_employee 回填 name/status/departments
        cur.execute("""
            UPDATE ext_follow_user f
            LEFT JOIN org_employee e ON e.userid=f.userid
            SET f.name=e.name, f.status=e.status, f.departments=e.departments
        """)

    print(json.dumps({
        "ok": True,
        "follow_users": len(incoming),
        "deleted": len(to_del) if incoming else 0
    }, ensure_ascii=False))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        sys.exit(1)