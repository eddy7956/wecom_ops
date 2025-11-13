from flask import Flask


def create_app():
    app = Flask(__name__)

    app.url_map.strict_slashes = False
    # 延迟导入，避免启动阶段因某模块未就绪而崩
    from app.api.v1 import v1
    from app.api.v1.blueprints import register_v1_blueprints
    from app.core.tracing import init_tracing

    app.register_blueprint(v1)
    init_tracing(app)
    register_v1_blueprints(app)

    # 统一错误为 JSON
    from werkzeug.exceptions import HTTPException
    from flask import jsonify
    @app.errorhandler(Exception)
    def _all_errors(e):
        if isinstance(e, HTTPException):
            return jsonify(ok=False, error={"code": e.name.replace(" ", "_").upper(), "message": e.description}), e.code
        return jsonify(ok=False, error={"code": "INTERNAL_ERROR", "message": str(e)}), 500

    # 最小健康探针
    @app.get("/healthz")
    def healthz():
        return {"ok": True, "data": "pong"}

    return app

# 可选：如果你依然用 app.app:app 启动，这行能兼容
app = create_app() if 'create_app' in globals() else app
