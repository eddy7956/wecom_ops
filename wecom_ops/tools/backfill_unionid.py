#!/usr/bin/env python3
# coding: utf-8
"""
独立执行的回填脚本：
- 读取 ext_contact 中 unionid 为空的 external_userid
- 调用企业微信「获取外部联系人详情」接口取 unionid
- 回填到 ext_contact.unionid
设计对齐：
- 复用项目封装的 get_conn()
- 不改现有蓝图/服务逻辑；可反复执行，幂等
"""

import os
import time
import json
import typing as T
import traceback
import requests

# 复用项目的数据库连接封装（与现有设计一致）
from app.core.db import get_conn

# ===== 配置（用环境变量覆盖）=====
WX_CORP_ID         = os.getenv("WX_CORP_ID", "")
WX_CONTACT_SECRET  = os.getenv("WX_CONTACT_SECRET", "")  # 外部联系人Secret
BATCH_SIZE         = int(os.getenv("UF_BATCH_SIZE", "300"))   # 每批多少条去拉
SLEEP_BETWEEN_CALL = float(os.getenv("UF_SLEEP", "0.05"))     # 单次调用间隔，粗限速
DRY_RUN            = os.getenv("UF_DRY_RUN", "0") == "1"      # 只看不写库
MAX_ROWS           = int(os.getenv("UF_MAX_ROWS", "100000"))  # 本次最多处理多少行，防误操作
LOG_EVERY          = int(os.getenv("UF_LOG_EVERY", "100"))    # 每处理多少条打一条进度

# 企业微信错误码，常用需刷新 token 的场景
NEED_REFRESH_ERRCODES = {40014, 42001, 41001}  # access_token 无效/过期/缺失


def _get_token(corpid: str, secret: str) -> str:
    r = requests.get(
        "https://qyapi.weixin.qq.com/cgi-bin/gettoken",
        params={"corpid": corpid, "corpsecret": secret},
        timeout=8,
    )
    r.raise_for_status()
    data = r.json()
    if data.get("errcode") != 0:
        raise RuntimeError(f"gettoken failed: {data}")
    return data["access_token"]


def _get_unionid(token: str, external_userid: str) -> T.Tuple[T.Optional[str], T.Optional[int]]:
    """返回 (unionid, errcode)。成功时 errcode 为 0。"""
    r = requests.get(
        "https://qyapi.weixin.qq.com/cgi-bin/externalcontact/get",
        params={"access_token": token, "external_userid": external_userid},
        timeout=8,
    )
    r.raise_for_status()
    data = r.json()
    err = data.get("errcode", -1)
    if err == 0:
        u = (data.get("external_contact") or {}).get("unionid")
        return u, 0
    return None, err


def main():
    if not WX_CORP_ID or not WX_CONTACT_SECRET:
        raise SystemExit("请先导出环境变量 WX_CORP_ID 与 WX_CONTACT_SECRET")

    # 先统计一下
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT COUNT(*) FROM ext_contact WHERE unionid IS NULL")
            total_null = c.fetchone()[0]
    print(f"[info] ext_contact.unionid IS NULL = {total_null}")

    if total_null == 0:
        print("[ok] 无需回填，已全部齐全。")
        return

    token = _get_token(WX_CORP_ID, WX_CONTACT_SECRET)
    processed = 0
    updated   = 0
    failed    = 0

    while processed < total_null and processed < MAX_ROWS:
        left = min(BATCH_SIZE, total_null - processed, MAX_ROWS - processed)
        if left <= 0:
            break

        # 取一批待回填
        with get_conn() as conn:
            with conn.cursor() as c:
                c.execute(
                    "SELECT external_userid FROM ext_contact WHERE unionid IS NULL LIMIT %s",
                    (left,),
                )
                batch_eids = [r[0] for r in c.fetchall()]

        if not batch_eids:
            break

        # 逐个调用企业微信接口
        for idx, eid in enumerate(batch_eids, 1):
            try:
                u, err = _get_unionid(token, eid)
                # 处理 token 失效/过期
                if err in NEED_REFRESH_ERRCODES:
                    token = _get_token(WX_CORP_ID, WX_CONTACT_SECRET)
                    u, err = _get_unionid(token, eid)

                if err == 0 and u:
                    if DRY_RUN:
                        # 预览模式不落库
                        pass
                    else:
                        with get_conn() as conn:
                            with conn.cursor() as c:
                                c.execute(
                                    "UPDATE ext_contact SET unionid=%s WHERE external_userid=%s",
                                    (u, eid),
                                )
                                conn.commit()
                    updated += 1
                else:
                    failed += 1
                    if err and err != 0:
                        # 常见：40096 非法的外部联系人userid；当做失败跳过
                        print(f"[warn] eid={eid} get unionid err={err}")
                processed += 1

                if processed % LOG_EVERY == 0:
                    print(f"[progress] processed={processed}, updated={updated}, failed={failed}")

            except Exception:
                failed += 1
                processed += 1
                traceback.print_exc()

            time.sleep(SLEEP_BETWEEN_CALL)

        # 再次粗略统计剩余（非强一致，只作为参考日志）
        with get_conn() as conn:
            with conn.cursor() as c:
                c.execute("SELECT COUNT(*) FROM ext_contact WHERE unionid IS NULL")
                total_null = c.fetchone()[0]

    print(f"[done] processed={processed}, updated={updated}, failed={failed}")
    with get_conn() as conn:
        with conn.cursor() as c:
            c.execute("SELECT COUNT(*) FROM ext_contact WHERE unionid IS NULL")
            left = c.fetchone()[0]
    print(f"[left] ext_contact.unionid IS NULL = {left}")


if __name__ == "__main__":
    main()
