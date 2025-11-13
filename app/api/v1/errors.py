from flask import jsonify, g

class ApiError(Exception):
    def __init__(self, code: str, message: str, http=400):
        self.code = code
        self.message = message
        self.http = http

def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def _api_error(e: ApiError):
        resp = jsonify({
            "ok": False,
            "error": {"code": e.code, "message": e.message},
            "trace_id": getattr(g, "trace_id", None),
        })
        resp.status_code = e.http
        return resp

    @app.errorhandler(404)
    def _not_found(_):
        return _api_error(ApiError("NOT_FOUND", "route not found", 404))

    @app.errorhandler(Exception)
    def _internal(e):
        return _api_error(ApiError("INTERNAL_ERROR", str(e), 500))
