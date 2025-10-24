# -*- coding: utf-8 -*-
"""
WSGI entry point:
- load optional .env
- build the Flask app
"""
from importlib import import_module
import os

try:
    from dotenv import load_dotenv

    dotenv_path = os.getenv("WECOM_OPS_DOTENV", "/www/wwwroot/wecom_ops/.env")
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
except Exception:
    pass

_appmod = import_module("app.app")
app = getattr(_appmod, "app", None)
if app is None and hasattr(_appmod, "create_app"):
    app = _appmod.create_app()
if app is None:
    raise RuntimeError("Unable to build Flask app: expose `app` or `create_app()` in app/app.py")
