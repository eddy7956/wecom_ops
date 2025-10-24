import logging
from flask import Blueprint, current_app

logger = logging.getLogger(__name__)

v1 = Blueprint("v1", __name__, url_prefix="/api/v1")


def _safe_register(module_path: str, attr: str = "bp") -> None:
    """Register optional blueprints onto v1 if the module exists."""
    try:
        module = __import__(module_path, fromlist=[attr])
    except ImportError as exc:
        logger.debug("Skipping optional v1 blueprint %s (%s)", module_path, exc)
        return
    blueprint = getattr(module, attr, None)
    if blueprint is None:
        raise AttributeError(f"{module_path} missing attribute {attr}")
    v1.register_blueprint(blueprint)


# Keep compatibility with legacy v1 submodules when present.
_safe_register("app.api.v1.mass.routes")


@v1.route("/__routes", methods=["GET"])
def __routes():
    routes = []
    for rule in current_app.url_map.iter_rules():
        methods = sorted(method for method in rule.methods if method not in {"HEAD", "OPTIONS"})
        routes.append({"rule": str(rule), "methods": methods})
    return {"ok": True, "data": routes}
