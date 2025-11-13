import uuid
from flask import g, request


def init_tracing(app):
    """Attach request/response hooks once per Flask app instance."""

    if getattr(app, "_tracing_initialized", False):
        return app

    @app.before_request
    def _bind_trace():
        g.trace_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())

    @app.after_request
    def _send_trace(resp):
        resp.headers.setdefault("X-Request-Id", g.get("trace_id", ""))
        return resp

    app._tracing_initialized = True
    return app
