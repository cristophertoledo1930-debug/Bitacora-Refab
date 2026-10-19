from fastapi.testclient import TestClient
from zoneinfo import ZoneInfo
from lab_hub.config import get_settings
from lab_hub.api.app import app

client = TestClient(app)


def test_timezone_santiago():
    settings = get_settings()
    tz = settings.timezone
    assert isinstance(tz, ZoneInfo)
    assert tz.key == "America/Santiago"


def test_health_live():
    res = client.get("/health/live")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "service": "qr-lab-hub"}


def test_health_ready():
    res = client.get("/health/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"

