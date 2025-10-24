# app/common/audit.py
from flask import request
import logging

try:
    from app.core.db import get_mysql_conn
except Exception:
    get_mysql_conn = None

def log(action: str, resource_type: str, resource_id: str, result: str, detail=None):
    operator = request.headers.get("X-Admin-User", "admin")
    # 没有 DB 也不阻塞主流程
    if not get_mysql_conn:
        logging.warning("[audit-skip] %s %s/%s result=%s (no db)", action, resource_type, resource_id, result)
        return
    try:
        sql = """
          INSERT INTO operation_log(operator, action, resource_type, resource_id, result, detail)
          VALUES (%s, %s, %s, %s, %s, %s)
        """
        conn = get_mysql_conn(); cur = conn.cursor()
        cur.execute(sql, (
            operator, action, resource_type, resource_id, result,
            detail if isinstance(detail, str) else (str(detail) if detail is not None else None)
        ))
        conn.commit(); cur.close(); conn.close()
    except Exception as e:
        logging.exception("[audit-fail] %s %s/%s result=%s err=%s", action, resource_type, resource_id, result, e)
        # 不 raise，保证业务接口继续返回
