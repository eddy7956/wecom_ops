import sys
import types
requests_stub = types.SimpleNamespace(get=None)
sys.modules.setdefault("requests", requests_stub)

from app.common import wecom_api

