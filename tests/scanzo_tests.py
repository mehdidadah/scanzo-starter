"""
Tests principaux (scanzo_tests.py)
- Regroupe une exécution simple/smoke sur les principaux composants
- Les tests détaillés sont répartis dans test_models.py, test_services.py, test_endpoints.py, test_integration.py, test_performance.py, test_utils.py
"""

from fastapi.testclient import TestClient
from app.main import app


def test_smoke_health_and_root():
    client = TestClient(app)
    # Root
    r = client.get("/")
    assert r.status_code == 200
    assert r.json().get("status") == "running"
    # Health
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json().get("status") == "up"
