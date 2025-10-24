# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Optional, Dict, Any
from app.core.db import get_mysql_conn

def upsert_external_contact(external_userid: str,
                            detail_json: Optional[Dict[str, Any]] = None,
                            source: str = "callback") -> int:
    """
    唯一写库点（幂等）：
    - 若提供 detail_json：写 ext_contact.detail_json，并尽量补齐结构化字段
    - 未提供 detail_json：仅刷新 updated_at，先留“打点”
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_mysql_conn() as conn:
        cur = conn.cursor()
        # 确保有记录
        cur.execute("""
            INSERT INTO wecom_ops.ext_contact (external_userid, created_at, updated_at)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE updated_at=VALUES(updated_at)
        """, (external_userid, now, now))
        affected = cur.rowcount

        if detail_json:
            name    = detail_json.get("name") or detail_json.get("Name")
            avatar  = detail_json.get("avatar") or detail_json.get("Avatar")
            unionid = detail_json.get("unionid") or detail_json.get("UnionId") or detail_json.get("union_id")
            corp    = detail_json.get("corp_name") or detail_json.get("CorpName") or detail_json.get("corp_full_name")

            cur.execute("""
                UPDATE wecom_ops.ext_contact
                SET detail_json=%s,
                    name=COALESCE(%s, name),
                    avatar=COALESCE(%s, avatar),
                    unionid=COALESCE(%s, unionid),
                    corp_name=COALESCE(%s, corp_name),
                    updated_at=%s
                WHERE external_userid=%s
            """, (str(detail_json), name, avatar, unionid, corp, now, external_userid))
            affected += cur.rowcount

        conn.commit()
        return affected
