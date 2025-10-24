# 标记为包；顺带导出 bp 便于调试（可有可无）
try:
    from .routes_v1 import bp  # noqa: F401
except Exception:
    bp = None
