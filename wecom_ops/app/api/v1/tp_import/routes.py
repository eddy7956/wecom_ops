from flask import Blueprint, request
from app.common.response import ok, err
import csv, io, secrets, time

bp = Blueprint("tp_import", __name__, url_prefix="/import")

# 简单内存缓存：生产可改成落盘或入库，这里满足联调
_UPLOAD_CACHE = {}  # token -> {"user_names":[...], "created_at":...}

@bp.route("/usernames/upload", methods=["POST"])
def upload_usernames():
    """
    支持 multipart/form-data 上传 CSV：
    - 表头含 user_name 或第一列视为 user_name
    - 返回 upload_token，后续在 targets_spec.mode=by_upload_token 使用
    """
    if "file" not in request.files:
        return err("BAD_REQUEST", "missing file", 400)

    f = request.files["file"]
    content = f.read().decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(content))
    user_names = []

    if reader.fieldnames and "user_name" in [c.strip() for c in reader.fieldnames]:
        col = [c for c in reader.fieldnames if c.strip() == "user_name"][0]
        for row in reader:
            val = (row.get(col) or "").strip()
            if val:
                user_names.append(val)
    else:
        # 没有表头时，按第一列
        reader2 = csv.reader(io.StringIO(content))
        for row in reader2:
            if not row: continue
            val = (row[0] or "").strip()
            if val and val.lower() != "user_name":
                user_names.append(val)

    if not user_names:
        return err("BAD_DATA", "no valid user_name in file", 422)

    token = f"U{int(time.time())}-{secrets.token_hex(8)}"
    _UPLOAD_CACHE[token] = {"user_names": list(dict.fromkeys(user_names)),
                            "created_at": int(time.time())}

    return ok({"upload_token": token, "count": len(user_names)})

def take_usernames_by_token(upload_token: str):
    v = _UPLOAD_CACHE.get(upload_token)
    return (v or {}).get("user_names") or []
