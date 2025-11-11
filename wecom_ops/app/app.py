from flask import Flask, jsonify, g
from werkzeug.exceptions import HTTPException


def create_app():
    app = Flask(__name__)
    app.url_map.strict_slashes = False

    # 延迟导入避免循环依赖
    from app.api.v1 import v1
    app.register_blueprint(v1)

    from app.api.v1.blueprints import register_v1_blueprints
    register_v1_blueprints(app)

    from app.core.tracing import init_tracing
    init_tracing(app)

    @app.errorhandler(Exception)
    def _all_errors(err):
        if isinstance(err, HTTPException):
            payload = {
                "ok": False,
                "error": {
                    "code": err.name.replace(" ", "_").upper(),
                    "message": err.description,
                },
            }
            response = jsonify(payload)
            response.status_code = err.code
        else:
            response = jsonify({"ok": False, "error": {"code": "INTERNAL_ERROR", "message": str(err)}})
            response.status_code = 500
        response.headers["X-Request-Id"] = getattr(g, "trace_id", "")
        return response

    @app.get("/healthz")
    def healthz():
        trace_id = getattr(g, "trace_id", "")
        payload = {"ok": True, "data": {"status": "OK"}, "trace_id": trace_id}
        resp = jsonify(payload)
        resp.headers["X-Request-Id"] = trace_id
        return resp, 200

    return app


app = create_app()
