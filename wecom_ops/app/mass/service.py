import math
from app.mass import repo

class ConflictError(Exception): ...
class ForbiddenError(Exception): ...
class ValidationError(Exception): ...

def create_task(body: dict) -> int:
    if not body.get("task_no"):
        raise ValidationError("task_no required")
    if not body.get("content_type"):
        raise ValidationError("content_type required")
    return repo.create_task_row(body)

def list_tasks(q: dict) -> dict:
    page = int(q.get("page",1)); size = int(q.get("size",20))
    q = {**q, "page":page, "size":size}
    return repo.page_tasks(q)

def get_task(task_id:int):
    return repo.get_task_row(task_id)

def update_task(task_id:int, patch:dict):
    row = repo.get_task_row(task_id)
    if not row: raise ValidationError("task not found")
    if row["status"] not in (0,1):
        raise ForbiddenError("task not editable in current status")
    repo.update_task_fields(task_id, patch)

def delete_task(task_id:int):
    row = repo.get_task_row(task_id)
    if not row: return
    if row["status"] not in (0,1):
        raise ForbiddenError("task not deletable in current status")
    repo.delete_task(task_id)

def plan_task(task_id:int) -> dict:
    row = repo.get_task_row(task_id)
    if not row: raise ValidationError("task not found")
    if row["status"] != 0:
        raise ForbiddenError("task already planned or not in draft")

    spec = row.get("targets_spec") or {}
    mode = spec.get("mode","all_contacts")
    limit = int(spec.get("limit") or 50000)

    if mode == "all_contacts":
        recipients = repo.pick_all_contacts(limit)
    elif mode == "by_tag_ids":
        recipients = repo.pick_by_tag_ids(spec.get("tag_ids") or [], limit)
    else:
        raise ValidationError(f"mode '{mode}' not supported")

    total = len(recipients)
    if total == 0: raise ValidationError("no recipients selected")

    gs = row.get("gray_strategy") or {"mode":"percent","waves":[{"pct":100}]}
    waves = gs.get("waves") or [{"pct":100}]
    batch_size = int(row.get("batch_size") or 300)

    # 计算每波条数
    counts, remain = [], total
    for i, w in enumerate(waves, start=1):
        pct = float(w.get("pct", 0))
        cnt = int(round(total * pct / 100.0)) if i < len(waves) else remain
        cnt = max(cnt, 0)
        counts.append(cnt); remain -= cnt
    if remain != 0: counts[-1] += remain

    # 生成快照
    snapshots = []
    offset = 0
    for wave_no, cnt in enumerate(counts, start=1):
        if cnt <= 0: continue
        seg = recipients[offset: offset+cnt]; offset += cnt
        batches = math.ceil(len(seg)/batch_size)
        for b in range(batches):
            part = seg[b*batch_size:(b+1)*batch_size]
            for rid in part:
                snapshots.append({"recipient_id": rid, "wave_no": wave_no, "batch_no": b+1})

    inserted = repo.insert_snapshots(task_id, snapshots)
    repo.set_task_status(task_id, 1)  # planned
    return {
        "task_id": task_id,
        "total": total,
        "inserted": inserted,
        "batch_size": batch_size,
        "waves": [{"wave_no": i+1, "size": c} for i, c in enumerate(counts)]
    }

def list_targets(task_id:int, state:str|None, page:int, size:int) -> dict:
    return repo.page_snapshots(task_id, state, page, size)

def list_logs(task_id:int, level:str|None, q:str|None, page:int, size:int) -> dict:
    return repo.list_logs(task_id, level, q, page, size)

# BEGIN_CONTROL

import datetime
from app.mass import repo

STATUS_DRAFT=0
STATUS_PLANNED=1
STATUS_RUNNING=2
STATUS_PAUSED=3
STATUS_FINISHED=4
STATUS_RECALLED=5

def start_task(task_id:int)->dict:
    t = repo.get_task(task_id)
    if not t: raise ValidationError("task not found")
    if t["status"] not in (STATUS_PLANNED, STATUS_PAUSED):
        raise ValidationError("task not in planned/paused")
    repo.update_task(task_id, {
        "status": STATUS_RUNNING,
        "started_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    return repo.get_task(task_id)

def pause_task(task_id:int):
    t = repo.get_task(task_id)
    if not t or t["status"] != STATUS_RUNNING:
        raise ValidationError("task not running")
    repo.update_task(task_id, {"status": STATUS_PAUSED})

def resume_task(task_id:int):
    t = repo.get_task(task_id)
    if not t or t["status"] != STATUS_PAUSED:
        raise ValidationError("task not paused")
    repo.update_task(task_id, {"status": STATUS_RUNNING})

def recall_task(task_id:int)->int:
    # 把待发的标记为 recalled，并标记任务为 RECALL
    n = repo.recall_pending_targets(task_id)
    repo.update_task(task_id, {"status": STATUS_RECALLED, "finished_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    return n

def stats_task(task_id:int)->dict:
    return repo.aggregate_task_stats(task_id)

# END_CONTROL
