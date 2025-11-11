import sys
import types

import pytest

requests_stub = types.SimpleNamespace(get=None)
sys.modules.setdefault("requests", requests_stub)

from app.common import wecom_api


class _FakeResp:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")


@pytest.fixture(autouse=True)
def _reset_env(monkeypatch):
    monkeypatch.setenv("WECOM_CORP_ID", "corp")
    monkeypatch.setenv("WECOM_CONTACTS_SECRET", "secret")
    monkeypatch.setenv("WECOM_AGENT_SECRET", "agent-secret")
    monkeypatch.setenv("WECOM_EXT_SECRET", "ext-secret")
    monkeypatch.setenv("WECOM_KF_SECRET", "kf-secret")
    monkeypatch.setattr(wecom_api, "_tok_cache", {})


def test_wecom_get_evicts_invalid_token(monkeypatch):
    state = {"token_calls": 0, "api_calls": 0}

    def fake_sleep(*_args, **_kwargs):
        return None

    def fake_get(url, params=None, timeout=None):
        if url.endswith("/cgi-bin/gettoken"):
            state["token_calls"] += 1
            token = f"token{state['token_calls']}"
            return _FakeResp(200, {"errcode": 0, "access_token": token, "expires_in": 7200})

        state["api_calls"] += 1
        if state["api_calls"] == 1:
            return _FakeResp(200, {"errcode": 40014})
        return _FakeResp(200, {"errcode": 0, "data": {"ok": True}, "token": params.get("access_token")})

    monkeypatch.setattr(wecom_api, "requests", type("_Requests", (), {"get": staticmethod(fake_get)}))
    monkeypatch.setattr(wecom_api, "_sleep_backoff", fake_sleep)

    result = wecom_api.wecom_get("/cgi-bin/user/get", params={"userid": "alice"}, max_retry=3)

    assert result["data"]["ok"] is True
    assert result["token"] == "token2"
    assert state["token_calls"] == 2
