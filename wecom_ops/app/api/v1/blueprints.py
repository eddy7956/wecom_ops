import logging
from flask import Blueprint, g

from app.common import response

logger = logging.getLogger(__name__)


def _safe_import(mod_path: str, attr: str = "bp"):
    """Best-effort import for optional blueprints."""
    try:
        module = __import__(mod_path, fromlist=[attr])
    except ImportError as exc:
        logger.debug("Skipping optional blueprint %s (%s)", mod_path, exc)
        return None
    value = getattr(module, attr, None)
    if value is None:
        raise AttributeError(f"{mod_path} missing attribute {attr}")
    return value


# Prefer routes_v1; fall back to legacy routes for gradual migration.
org_bp = _safe_import("app.org.routes_v1") or _safe_import("app.org.routes")
ext_bp = _safe_import("app.ext.routes_v1") or _safe_import("app.ext.routes")
id_bp = _safe_import("app.identity.routes_v1") or _safe_import("app.identity.routes")
members_bp = _safe_import("app.members.routes_v1") or _safe_import("app.members.routes")
mass_bp = _safe_import("app.mass.routes_v1") or _safe_import("app.mass.routes")
media_bp = _safe_import("app.media.routes_v1") or _safe_import("app.media.routes")
wecom_bp = _safe_import("app.wecom.routes_v1") or _safe_import("app.wecom.routes")


# /api/v1/health
health_bp = Blueprint("health_api", __name__, url_prefix="/api/v1")


@health_bp.get("/health")
def health():
    trace_id = getattr(g, "trace_id", "")
    return response.ok(extra={"trace_id": trace_id})


def register_v1_blueprints(app):
    def has_prefix(prefix: str) -> bool:
        try:
            return any(str(rule.rule).startswith(prefix) for rule in app.url_map.iter_rules())
        except Exception:
            return False

    if not has_prefix("/api/v1/health"):
        app.register_blueprint(health_bp)

    mapping = [
        (org_bp, "/api/v1/org"),
        (ext_bp, "/api/v1/ext"),
        (id_bp, "/api/v1/identity"),
        (members_bp, "/api/v1/members"),
        (mass_bp, "/api/v1/mass"),
        (media_bp, "/api/v1/media"),
        (wecom_bp, "/api/v1/wecom"),
    ]
    for bp, prefix in mapping:
        if bp and not has_prefix(prefix):
            app.register_blueprint(bp)
