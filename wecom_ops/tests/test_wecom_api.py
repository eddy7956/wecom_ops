import sys
import types

requests_stub = types.SimpleNamespace(get=None)
sys.modules.setdefault("requests", requests_stub)

from app.common import wecom_api


def _make_response(payload, status_code=200):
    resp = types.SimpleNamespace()
    resp.status_code = status_code

    def _json():
        return payload

    def _raise():
        if status_code >= 400:
            raise RuntimeError(f"HTTP {status_code}")

    resp.json = _json
    resp.raise_for_status = _raise
    return resp


def test_wecom_get_refreshes_token_on_invalid(monkeypatch):
    monkeypatch.setenv("WECOM_CORP_ID", "corp")
    monkeypatch.setenv("WECOM_CONTACTS_SECRET", "secret")
    monkeypatch.setattr(wecom_api, "_sleep_backoff", lambda *_, **__: None)
    monkeypatch.setattr(wecom_api, "_tok_cache", {})

    initial_expiry = wecom_api._now() + 600
    wecom_api._tok_cache["WECOM_CONTACTS_SECRET"] = ("stale-token", initial_expiry)

    call_state = {"gettoken": 0, "api_tokens": []}

    def fake_get(url, params=None, timeout=None):
        if url.endswith("/cgi-bin/gettoken"):
            call_state["gettoken"] += 1
            return _make_response({
                "errcode": 0,
                "access_token": "fresh-token",
                "expires_in": 7200,
            })

        call_state["api_tokens"].append(params.get("access_token"))
        if params.get("access_token") == "stale-token":
            return _make_response({"errcode": 40014})
        return _make_response({"errcode": 0, "result": "ok"})

    monkeypatch.setattr(wecom_api.requests, "get", fake_get)

    data = wecom_api.wecom_get("/cgi-bin/user/get", {"userid": "abc"})

    assert data["result"] == "ok"
    assert call_state["api_tokens"] == ["stale-token", "fresh-token"]
    assert call_state["gettoken"] == 1
    assert wecom_api._tok_cache["WECOM_CONTACTS_SECRET"][0] == "fresh-token"
