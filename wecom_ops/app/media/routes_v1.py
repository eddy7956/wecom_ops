from flask import Blueprint, request, jsonify, g
from app.core.db import get_mysql_conn as get_conn
import csv, io, re, traceback

bp = Blueprint("media_v1", __name__, url_prefix="/api/v1/media")

def j(payload, http=200):
    resp = jsonify(payload)
    try:
        resp.headers.setdefault("X-Request-Id", getattr(g, "trace_id",""))
    except Exception:
        pass
    return resp, http

def _norm_mobile(s: str) -> str:
    digits = re.sub(r"\D+", "", s or "")
    if digits.startswith("86") and len(digits) > 11:
        digits = digits[2:]
    return digits if len(digits) == 11 else ""

@bp.post("/upload")
def upload():
    try:
        up_type = (request.form.get("type") or "").strip()
        f = request.files.get("file")
        if up_type != "mobile_list":
            return j({"ok": False, "error": {"code":"VALIDATION_ERROR","message":"type must be mobile_list"}}, 400)
        if not f:
            return j({"ok": False, "error": {"code":"VALIDATION_ERROR","message":"file required"}}, 400)

        filename = f.filename or "upload.csv"
        data = f.read()
        # 以 CSV 解析
        try:
            text = data.decode("utf-8-sig", errors="ignore")
        except Exception:
            text = data.decode("utf-8", errors="ignore")

        reader = csv.reader(io.StringIO(text))
        mobiles = set()
        for row in reader:
            for col in row:
                m = _norm_mobile(col)
                if m:
                    mobiles.add(m)

        mobiles = list(mobiles)
        conn = get_conn()
        with conn.cursor() as cur:
            # 主表
            cur.execute(
                "INSERT INTO wecom_ops.mobile_upload(type, filename, total, valid, invalid) VALUES(%s,%s,0,0,0)",
                (up_type, filename)
            )
            upload_id = cur.lastrowid

            # 明细（去重）
            if mobiles:
                vals = [(upload_id, m) for m in mobiles]
                BATCH = 1000
                for i in range(0, len(vals), BATCH):
                    part = vals[i:i+BATCH]
                    cur.executemany(
                        "INSERT IGNORE INTO wecom_ops.mobile_upload_item(upload_id, mobile_std) VALUES(%s,%s)", part
                    )

            # 统计：注意起别名 AS cnt，并兼容 DictCursor/tuple 两种返回
            cur.execute(
                "SELECT COUNT(*) AS cnt FROM wecom_ops.mobile_upload_item WHERE upload_id=%s",
                (upload_id,)
            )
            row = cur.fetchone()
            total = int(row.get('cnt') if isinstance(row, dict) else row[0])

            cur.execute("""
                SELECT COUNT(DISTINCT i.mobile_std) AS cnt
                FROM wecom_ops.mobile_upload_item i
                JOIN wecom_ops.vw_mobile_to_external v
                  ON v.mobile_std = i.mobile_std
                WHERE i.upload_id = %s
            """, (upload_id,))
            row = cur.fetchone()
            valid = int(row.get('cnt') if isinstance(row, dict) else row[0])

            invalid = max(total - valid, 0)

            # 回写主表
            cur.execute(
              "UPDATE wecom_ops.mobile_upload SET total=%s, valid=%s, invalid=%s WHERE id=%s",
              (total, valid, invalid, upload_id)
            )

        return j({"ok": True, "data": {"upload_id": int(upload_id), "total": total, "valid": valid, "invalid": invalid}})
    except Exception as e:
        return j({"ok": False, "error": {"code":"INTERNAL_ERROR","message":str(e),"detail":traceback.format_exc()}}, 500)
