import pytest
from app.app import create_app
from app.common.retry import expo_backoff

@pytest.fixture(scope="module")
def client():
    app = create_app()
    app.testing = True
    return app.test_client()

def test_health_has_trace_id(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    j = r.get_json()
    assert j["ok"] is True
    assert j.get("trace_id")
    assert r.headers.get("X-Request-Id")

# 生成 20+ 条用例：指数退避的边界/增长
@pytest.mark.parametrize(
    "attempt,base,unit,expected_min",
    [
        (0,2.0,1.0,1.0),(1,2.0,1.0,2.0),(2,2.0,1.0,4.0),(3,2.0,1.0,8.0),
        (4,2.0,1.0,16.0),(5,2.0,1.0,32.0),(1,3.0,1.0,3.0),(2,3.0,1.0,9.0),
        (3,3.0,1.0,27.0),(0,2.0,0.5,0.5),(1,2.0,0.5,1.0),(2,2.0,0.5,2.0),
        (3,2.0,0.5,4.0),(4,2.0,0.5,8.0),(5,2.0,0.5,16.0),(6,2.0,0.5,32.0),
        (7,2.0,0.5,64.0),(8,2.0,0.5,128.0),(9,2.0,0.5,256.0),(10,2.0,0.5,512.0),
    ],
)
def test_expo_backoff(attempt, base, unit, expected_min):
    assert expo_backoff(attempt, base, unit) >= expected_min
