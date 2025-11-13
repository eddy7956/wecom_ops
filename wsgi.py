# -*- coding: utf-8 -*-
"""
稳定版 WSGI 入口（唯一机制）：
- 加载 .env
- 构建 app 实例
- 启用 TraceID
- 注册 /api/v1 蓝图
"""
import os
from importlib import import_module
try:
    from dotenv import load_dotenv
    load_dotenv("/www/wwwroot/wecom_ops/.env")
except Exception:
    pass

from app.core.tracing import init_tracing
from app.api.v1.blueprints import register_v1_blueprints

_appmod = import_module("app.app")
app = getattr(_appmod, "app", None)
if app is None and hasattr(_appmod, "create_app"):
    app = _appmod.create_app()
if app is None:
    raise RuntimeError("无法构建 Flask app：请在 app/app.py 中提供 app 或 create_app()")

init_tracing(app)
register_v1_blueprints(app)
