from flask import current_app
from typing import Dict, Any, List, Tuple
from math import ceil
from app.core.db import get_mysql_conn
from app.mass import repo

def _load_candidates_by_spec(targets_spec: Dict[str, Any]) -> List[str]:
    mode = targets_spec.get("mode") or "all_contacts"
    limit = int(targets_spec.get("limit") or 80000)
    sql, args = None, None
    if mode == "by_tag_ids":
        tag_ids = targets_spec.get("tag_ids") or []
        if not tag_ids:
            return []
        placeholders = ",".join(["%s"] * len(tag_ids))
        sql = f"""
          SELECT DISTINCT ect.external_userid
            FROM ext_contact_tag ect
           WHERE ect.tag_id IN ({placeholders})
           LIMIT %s
        """
        args = (*tag_ids, limit)
    else:
        sql = "SELECT external_userid FROM ext_contact LIMIT %s"
        args = (limit,)
    try:
        with get_mysql_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, args)
            return [row[0] for row in cur.fetchall() if row and row[0]]
    except Exception as e:
        # 表不存在/字段缺失等 -> 直接当 0 人群，避免炸
        try:
            current_app.logger.warning("plan.load_candidates_failed: %s", e)
        except Exception:
            pass
        return []

def _allocate_waves(total: int, gray: Dict[str, Any]) -> List[int]:
    """
    按灰度百分比分配每波条数；四舍五入，尾差调到最后一波
    gray = {"mode":"percent", "waves":[{"pct":1},{"pct":5},{"pct":20},{"pct":100}]}
    """
    waves = gray.get("waves") or []
    if not waves:
        waves = [{"pct":100}]
    qty = []
    acc = 0
    for i, w in enumerate(waves):
        pct = float(w.get("pct", 0))
        n = int(round(total * pct / 100.0))
        qty.append(n)
        acc += n
    if qty:
        qty[-1] += (total - acc)
    return [max(0, x) for x in qty]

def _batches_for_wave(n_items: int, batch_size: int) -> int:
    return max(1, ceil(n_items / max(1, batch_size)))

def plan_targets(task_id: int, targets_spec: Dict[str, Any], gray_strategy: Dict[str, Any], batch_size: int) -> Dict[str, Any]:
    # 1) 候选集
    candidates = _load_candidates_by_spec(targets_spec)
    total = len(candidates)

    # 2) 灰度→波次数量
    waves_qty = _allocate_waves(total, gray_strategy or {"waves":[{"pct":100}]})

    # 3) 生成 (recipient_id, shard_no, wave_no, batch_no)
    rows: List[Tuple[str,int,int,int]] = []
    offset = 0
    shard_no = 0
    for wave_no, n in enumerate(waves_qty, start=1):
        if n <= 0:
            continue
        batches = _batches_for_wave(n, batch_size)
        per_batch = ceil(n / batches)
        for b in range(1, batches+1):
            start = offset + (b-1)*per_batch
            end = min(offset + b*per_batch, offset + n)
            for recipient_id in candidates[start:end]:
                rows.append((recipient_id, shard_no, wave_no, b))
        offset += n

    # 4) 批量入库
    inserted = repo.bulk_insert_targets(task_id, rows)

    # 5) 汇总
    return {
        "task_id": task_id,
        "total": total,
        "waves": [{"wave_no": i+1, "size": waves_qty[i]} for i in range(len(waves_qty))],
        "batch_size": batch_size,
        "inserted": inserted
    }
