import pytest
import os

# 强制使用 SQLite 进行测试，避开 PostgreSQL 的连接问题
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from fastapi.testclient import TestClient
from main import app, webhook_token

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"

def test_webhook_unauthorized():
    response = client.post("/api/health/webhook?token=wrong-token", json={})
    assert response.status_code == 403

def test_webhook_authorized():
    # 使用默认的 token
    response = client.post(f"/api/health/webhook?token={webhook_token}", json={
        "data": {
            "metrics": [
                {
                    "name": "step_count",
                    "units": "steps",
                    "data": [{"qty": 100, "date": "2024-03-20 12:00:00"}]
                }
            ]
        }
    })
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
