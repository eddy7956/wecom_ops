from flask import Blueprint, jsonify, g

def _safe_import(mod_path, attr='bp'):
    try:
        mod = __import__(mod_path, fromlist=[attr])
        return getattr(mod, attr)
    except Exception:
        return None

# 优先 routes_v1，失败回退 routes（单一机制，但允许旧文件存在时渐进过渡）
org_bp   = _safe_import("app.org.routes_v1")      or _safe_import("app.org.routes")
ext_bp   = _safe_import("app.ext.routes_v1")      or _safe_import("app.ext.routes")
id_bp    = _safe_import("app.identity.routes_v1") or _safe_import("app.identity.routes")
members_bp = _safe_import("app.members.routes_v1")   or _safe_import("app.members.routes")
mass_bp  = _safe_import("app.mass.routes_v1")     or _safe_import("app.mass.routes")
media_bp = _safe_import("app.media.routes_v1")    or _safe_import("app.media.routes")
wecom_bp = _safe_import("app.wecom.routes_v1")    or _safe_import("app.wecom.routes")

# /api/v1/health
health_bp = Blueprint("health_api", __name__, url_prefix="/api/v1")
@health_bp.get("/health")
def health():
    payload = {"ok": True, "data": {"status": "OK"}, "trace_id": getattr(g, "trace_id", "")}
    resp = jsonify(payload)
    resp.headers["X-Request-Id"] = payload["trace_id"]
    return resp, 200

def register_v1_blueprints(app):
    if getattr(app, "_v1_blueprints_registered", False):
        return app

    def has_prefix(pfx: str):
        try:
            return any(str(r.rule).startswith(pfx) for r in app.url_map.iter_rules())
        except Exception:
            return False

    if not has_prefix("/api/v1/health"):
        app.register_blueprint(health_bp)

    mapping = [
        (org_bp,   "/api/v1/org"),
        (ext_bp,   "/api/v1/ext"),
        (id_bp,    "/api/v1/identity"),
        (mass_bp,  "/api/v1/mass"),
        (members_bp, "/api/v1/members"),
        (media_bp, "/api/v1/media"),
        (wecom_bp, "/api/v1/wecom"),
    ]
    for bp, prefix in mapping:
        if bp and not has_prefix(prefix):
            app.register_blueprint(bp)
    app._v1_blueprints_registered = True
    return app
