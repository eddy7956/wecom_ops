from flask import Blueprint

v1 = Blueprint("v1", __name__, url_prefix="/api/v1")

# 仅安全挂载已存在且可用的蓝图，避免顶层导入导致进程崩溃
def _safe_register(module_path: str, attr: str = "bp"):
    try:
        mod = __import__(module_path, fromlist=[attr])
        bp = getattr(mod, attr)
        v1.register_blueprint(bp)
    except Exception:
        # 这里故意忽略（也可写入日志），保证服务能启动
        pass

# ✅ 你已经跑通的 mass 路由（保留）
_safe_register("app.api.v1.mass.routes")

# ⏸️ 未来再打开的模块（等对应代码准备好再放开）
# _safe_register("app.api.v1.tp_import.routes")
# _safe_register("app.api.v1.org.routes")
# _safe_register("app.api.v1.ext.routes")
# _safe_register("app.api.v1.system.routes")

@v1.route("/__routes", methods=["GET"])
def __routes():
    from flask import current_app
    routes = []
    for r in current_app.url_map.iter_rules():
        methods = sorted([m for m in r.methods if m not in ("HEAD", "OPTIONS")])
        routes.append({"rule": str(r), "methods": methods})
    return {"ok": True, "data": routes}
