"""REST endpoints for the mass messaging module."""

from __future__ import annotations

from flask import Blueprint, jsonify, g, request

from app.mass import service
from app.mass.service import ConflictError, ForbiddenError, ValidationError

bp = Blueprint("mass_v1", __name__, url_prefix="/api/v1/mass")


def _response(ok: bool, data: dict | None = None, error: dict | None = None, status: int = 200):
    payload = {"ok": ok}
    trace_id = getattr(g, "trace_id", "")
    if ok:
        payload["data"] = data or {}
    else:
        payload["error"] = error or {"code": "INTERNAL_ERROR", "message": "unknown error"}
    if trace_id:
        payload["trace_id"] = trace_id
    resp = jsonify(payload)
    if trace_id:
        resp.headers["X-Request-Id"] = trace_id
    return resp, status


def _handle_error(exc: Exception):
    if isinstance(exc, ValidationError):
        code = "VALIDATION_ERROR"
        status = 400
        if str(exc) == "task not found":
            code = "NOT_FOUND"
            status = 404
        return _response(False, error={"code": code, "message": str(exc)}, status=status)
    if isinstance(exc, ForbiddenError):
        return _response(False, error={"code": "FORBIDDEN", "message": str(exc)}, status=403)
    if isinstance(exc, ConflictError):
        return _response(False, error={"code": "CONFLICT", "message": str(exc)}, status=409)
    return _response(False, error={"code": "INTERNAL_ERROR", "message": str(exc)}, status=500)


@bp.post("/tasks")
def create_task():
    body = request.get_json(silent=True) or {}
    try:
        task_id = service.create_task(body)
        return _response(True, {"task_id": task_id}, status=201)
    except Exception as exc:  # noqa: B902 - delegated to handler
        return _handle_error(exc)


@bp.get("/tasks")
def list_tasks():
    params = request.args.to_dict(flat=True)
    try:
        data = service.list_tasks(params)
        return _response(True, data)
    except Exception as exc:
        return _handle_error(exc)


@bp.get("/tasks/<int:task_id>")
def get_task(task_id: int):
    try:
        task = service.get_task(task_id)
        return _response(True, task)
    except Exception as exc:
        return _handle_error(exc)


@bp.patch("/tasks/<int:task_id>")
def update_task(task_id: int):
    body = request.get_json(silent=True) or {}
    try:
        service.update_task(task_id, body)
        return _response(True, {"task_id": task_id})
    except Exception as exc:
        return _handle_error(exc)


@bp.delete("/tasks/<int:task_id>")
def delete_task(task_id: int):
    try:
        service.delete_task(task_id)
        return _response(True, {"task_id": task_id})
    except Exception as exc:
        return _handle_error(exc)


@bp.post("/tasks/<int:task_id>/plan")
def plan_task(task_id: int):
    try:
        plan = service.plan_task(task_id)
        return _response(True, {"plan": plan})
    except Exception as exc:
        return _handle_error(exc)


@bp.get("/tasks/<int:task_id>/targets")
def list_targets(task_id: int):
    try:
        page = int(request.args.get("page", 1))
        size = int(request.args.get("size", 20))
        state = request.args.get("state") or None
        data = service.list_targets(task_id, state, page, size)
        return _response(True, data)
    except Exception as exc:
        return _handle_error(exc)


@bp.get("/tasks/<int:task_id>/logs")
def list_logs(task_id: int):
    try:
        page = int(request.args.get("page", 1))
        size = int(request.args.get("size", 20))
        level = request.args.get("level") or None
        keyword = request.args.get("q") or None
        data = service.list_logs(task_id, level, keyword, page, size)
        return _response(True, data)
    except Exception as exc:
        return _handle_error(exc)


@bp.post("/tasks/<int:task_id>/retry_failed")
def retry_failed(task_id: int):
    try:
        reset = service.retry_failed(task_id)
        return _response(True, {"task_id": task_id, "reset": reset})
    except Exception as exc:
        return _handle_error(exc)


@bp.post("/tasks/<int:task_id>/start")
def start_task(task_id: int):
    try:
        task = service.start_task(task_id)
        return _response(True, task)
    except Exception as exc:
        return _handle_error(exc)


@bp.post("/tasks/<int:task_id>/pause")
def pause_task(task_id: int):
    try:
        service.pause_task(task_id)
        return _response(True, {"task_id": task_id, "status": "PAUSED"})
    except Exception as exc:
        return _handle_error(exc)


@bp.post("/tasks/<int:task_id>/resume")
def resume_task(task_id: int):
    try:
        service.resume_task(task_id)
        return _response(True, {"task_id": task_id, "status": "RUNNING"})
    except Exception as exc:
        return _handle_error(exc)


@bp.post("/tasks/<int:task_id>/recall")
def recall_task(task_id: int):
    try:
        recalled = service.recall_task(task_id)
        return _response(True, {"task_id": task_id, "recalled": recalled})
    except Exception as exc:
        return _handle_error(exc)


@bp.get("/tasks/<int:task_id>/stats")
def stats_task(task_id: int):
    try:
        stats = service.stats_task(task_id)
        return _response(True, stats)
    except Exception as exc:
        return _handle_error(exc)
