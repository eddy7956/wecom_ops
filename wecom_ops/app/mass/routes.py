from flask import Blueprint, request, jsonify
from app.mass import repo
from app.mass.planner import plan_targets

bp = Blueprint("mass_api", __name__, url_prefix="/mass")

@bp.post("/tasks")
def create_task_api():
    data = request.get_json(force=True) or {}
    task_id = repo.create_task({
        "task_no": data.get("task_no"),
        "mass_type": data.get("mass_type") or "external_contact",
        "content_type": data.get("content_type") or "text",
        "content_json": data.get("content_json") or {"text":"hello"},
        "targets_spec": data.get("targets_spec") or {"mode":"all_contacts","limit":80000},
        "scheduled_at": data.get("scheduled_at"),
        "qps_limit": data.get("qps_limit") or 600,
        "concurrency_limit": data.get("concurrency_limit") or 20,
        "batch_size": data.get("batch_size") or 300,
        "gray_strategy": data.get("gray_strategy") or {"mode":"percent","waves":[{"pct":1},{"pct":5},{"pct":20},{"pct":100}]},
        "report_stat": {},
        "agent_id": data.get("agent_id"),
    })
    return jsonify({"ok": True, "task_id": task_id}), 201

@bp.post("/tasks/<int:task_id>/plan")
def plan_task_api(task_id: int):
    from flask import current_app
    try:
        t = repo.get_task(task_id)
        if not t:
            return jsonify({"ok": False, "error": {"code": "NOT_FOUND", "message": "task not found"}}), 404

        targets_spec = t.get("targets_spec") or {}
        gray = t.get("gray_strategy") or {"mode": "percent", "waves": [{"pct": 100}]}
        batch_size = t.get("batch_size") or 300

        result = plan_targets(task_id, targets_spec, gray, batch_size)
        repo.update_task_status(task_id, 1)  # 1=planned
        return jsonify({"ok": True, "plan": result}), 200

    except Exception as e:
        try:
            current_app.logger.exception("plan_task_failed task_id=%s", task_id)
        except Exception:
            pass
        return jsonify({"ok": False, "error": {"code": "INTERNAL_ERROR", "message": str(e)}}), 500
