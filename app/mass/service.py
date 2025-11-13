"""Business logic for the mass messaging module."""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List

from app.mass import repo


class ConflictError(RuntimeError):
    pass


class ForbiddenError(RuntimeError):
    pass


class ValidationError(RuntimeError):
    pass


STATUS_DRAFT = 0
STATUS_PLANNED = 1
STATUS_RUNNING = 2
STATUS_PAUSED = 3
STATUS_FINISHED = 4
STATUS_RECALLED = 5

STATUS_LABELS = {
    STATUS_DRAFT: "DRAFT",
    STATUS_PLANNED: "PLANNED",
    STATUS_RUNNING: "RUNNING",
    STATUS_PAUSED: "PAUSED",
    STATUS_FINISHED: "FINISHED",
    STATUS_RECALLED: "RECALLED",
}


def _ensure_task(task_id: int) -> Dict[str, Any]:
    task = repo.get_task(task_id)
    if not task:
        raise ValidationError("task not found")
    return task


def _default_gray_strategy(total: int) -> Dict[str, Any]:
    return {"mode": "percent", "waves": [{"pct": 100, "size": total}]}


def _annotate_status(task: Dict[str, Any]) -> Dict[str, Any]:
    enriched = dict(task)
    enriched["status_label"] = STATUS_LABELS.get(task.get("status"), "UNKNOWN")
    return enriched


def create_task(body: Dict[str, Any]) -> int:
    if not body.get("task_no"):
        raise ValidationError("task_no required")
    if not body.get("content_type"):
        raise ValidationError("content_type required")
    payload = {
        "task_no": body.get("task_no"),
        "name": body.get("name"),
        "mass_type": body.get("mass_type") or "external",
        "content_type": body.get("content_type"),
        "content_json": body.get("content_json") or {},
        "targets_spec": body.get("targets_spec") or {},
        "scheduled_at": body.get("scheduled_at"),
        "qps_limit": body.get("qps_limit"),
        "concurrency_limit": body.get("concurrency_limit"),
        "batch_size": body.get("batch_size"),
        "gray_strategy": body.get("gray_strategy") or {},
        "report_stat": body.get("report_stat") or {},
        "agent_id": body.get("agent_id"),
    }
    try:
        return repo.create_task(payload)
    except repo.DuplicateTaskNoError as exc:  # pragma: no cover - depends on DB schema
        raise ConflictError("task_no already exists") from exc


def list_tasks(params: Dict[str, Any]) -> Dict[str, Any]:
    page = int(params.get("page", 1))
    size = int(params.get("size", 20))
    result = repo.page_tasks({**params, "page": page, "size": size})
    result["items"] = [_annotate_status(it) for it in result.get("items", [])]
    return result


def get_task(task_id: int) -> Dict[str, Any]:
    return _annotate_status(_ensure_task(task_id))


def update_task(task_id: int, patch: Dict[str, Any]) -> None:
    task = _ensure_task(task_id)
    if task["status"] not in (STATUS_DRAFT, STATUS_PLANNED):
        raise ForbiddenError("task not editable in current status")
    allowed = {
        "name",
        "scheduled_at",
        "qps_limit",
        "concurrency_limit",
        "batch_size",
        "content_json",
        "targets_spec",
        "gray_strategy",
        "report_stat",
    }
    clean = {k: v for k, v in patch.items() if k in allowed}
    if not clean:
        return
    repo.update_task(task_id, clean)


def delete_task(task_id: int) -> None:
    _ensure_task(task_id)
    repo.delete_task(task_id)


def plan_task(task_id: int) -> Dict[str, Any]:
    task = _ensure_task(task_id)
    if task["status"] not in (STATUS_DRAFT, STATUS_PLANNED):
        raise ForbiddenError("task not in draft status")

    spec = task.get("targets_spec") or {}
    mode = spec.get("mode", "all_contacts")
    limit = int(spec.get("limit") or 50000)

    if mode == "all_contacts":
        recipients = repo.pick_all_contacts(limit)
    elif mode == "by_tag_ids":
        recipients = repo.pick_by_tag_ids(spec.get("tag_ids") or [], limit)
    else:
        raise ValidationError(f"unsupported targets_spec mode: {mode}")

    if not recipients:
        raise ValidationError("no recipients selected")

    batch_size = int(task.get("batch_size") or 300)
    gray_strategy = task.get("gray_strategy") or _default_gray_strategy(len(recipients))
    waves = gray_strategy.get("waves") or _default_gray_strategy(len(recipients))["waves"]

    counts: List[int] = []
    total = len(recipients)
    remain = total
    for idx, wave in enumerate(waves, start=1):
        pct = float(wave.get("pct", 0))
        cnt = int(round(total * pct / 100.0)) if idx < len(waves) else remain
        cnt = max(cnt, 0)
        counts.append(cnt)
        remain -= cnt
    if remain:
        counts[-1] += remain

    snapshots = []
    offset = 0
    for wave_no, count in enumerate(counts, start=1):
        if count <= 0:
            continue
        chunk = recipients[offset : offset + count]
        offset += count
        batches = (len(chunk) + batch_size - 1) // batch_size
        for batch_no in range(1, batches + 1):
            batch_slice = chunk[(batch_no - 1) * batch_size : batch_no * batch_size]
            snapshots.extend(
                {
                    "recipient_id": rid,
                    "wave_no": wave_no,
                    "batch_no": batch_no,
                    "state": "pending",
                }
                for rid in batch_slice
            )

    repo.clear_snapshots(task_id)
    inserted = repo.insert_snapshots(task_id, snapshots)
    repo.set_task_status(task_id, STATUS_PLANNED)

    plan = {
        "task_id": task_id,
        "total": total,
        "inserted": inserted,
        "batch_size": batch_size,
        "waves": [
            {"wave_no": index + 1, "size": count}
            for index, count in enumerate(counts)
            if count > 0
        ],
    }
    return plan


def list_targets(task_id: int, state: str | None, page: int, size: int) -> Dict[str, Any]:
    _ensure_task(task_id)
    return repo.page_snapshots(task_id, state, page, size)


def list_logs(task_id: int, level: str | None, keyword: str | None, page: int, size: int) -> Dict[str, Any]:
    _ensure_task(task_id)
    return repo.list_logs(task_id, level, keyword, page, size)


def retry_failed(task_id: int) -> int:
    _ensure_task(task_id)
    return repo.reset_failed_targets(task_id)


def start_task(task_id: int) -> Dict[str, Any]:
    task = _ensure_task(task_id)
    if task["status"] not in (STATUS_PLANNED, STATUS_PAUSED):
        raise ValidationError("task not in planned or paused state")
    repo.set_task_status(
        task_id,
        STATUS_RUNNING,
        {"started_at": dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")},
    )
    return get_task(task_id)


def pause_task(task_id: int) -> None:
    task = _ensure_task(task_id)
    if task["status"] != STATUS_RUNNING:
        raise ValidationError("task not running")
    repo.set_task_status(task_id, STATUS_PAUSED)


def resume_task(task_id: int) -> None:
    task = _ensure_task(task_id)
    if task["status"] != STATUS_PAUSED:
        raise ValidationError("task not paused")
    repo.set_task_status(task_id, STATUS_RUNNING)


def recall_task(task_id: int) -> int:
    task = _ensure_task(task_id)
    if task["status"] not in (STATUS_RUNNING, STATUS_PAUSED, STATUS_PLANNED):
        raise ValidationError("task not recallable")
    affected = repo.recall_pending_targets(task_id)
    repo.set_task_status(
        task_id,
        STATUS_RECALLED,
        {"finished_at": dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")},
    )
    return affected


def stats_task(task_id: int) -> Dict[str, Any]:
    _ensure_task(task_id)
    return repo.aggregate_task_stats(task_id)
