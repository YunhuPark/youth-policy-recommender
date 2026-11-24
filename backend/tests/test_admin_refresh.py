"""수동 정책 갱신 API의 관리자 토큰 검사 회귀 테스트."""
import pytest
from fastapi.testclient import TestClient

import main


class Scheduler:
    def __init__(self):
        self.calls = 0

    async def refresh_policies(self):
        self.calls += 1
        return {"success": True, "refreshed": self.calls}


@pytest.fixture
def api(monkeypatch):
    scheduler = Scheduler()
    monkeypatch.setattr(main, "get_scheduler", lambda: scheduler)
    monkeypatch.setattr(main.settings, "environment", "development")
    monkeypatch.delenv("ADMIN_REFRESH_TOKEN", raising=False)
    return TestClient(main.app), scheduler


def test_refresh_requires_token_when_configured(api, monkeypatch):
    client, scheduler = api
    monkeypatch.setenv("ADMIN_REFRESH_TOKEN", "s3cret-token")

    assert client.post("/api/scheduler/refresh").status_code == 401
    assert client.post(
        "/api/scheduler/refresh", headers={"X-Admin-Token": "wrong"}
    ).status_code == 401
    assert scheduler.calls == 0


def test_refresh_runs_with_matching_token(api, monkeypatch):
    client, scheduler = api
    monkeypatch.setenv("ADMIN_REFRESH_TOKEN", "s3cret-token")

    response = client.post("/api/scheduler/refresh", headers={"X-Admin-Token": "s3cret-token"})

    assert response.status_code == 200
    assert response.json() == {"success": True, "refreshed": 1}
    assert scheduler.calls == 1


def test_refresh_stays_open_in_development_without_token(api):
    client, scheduler = api

    response = client.post("/api/scheduler/refresh")

    assert response.status_code == 200
    assert scheduler.calls == 1


def test_refresh_is_blocked_in_production_without_token(api, monkeypatch):
    client, scheduler = api
    monkeypatch.setattr(main.settings, "environment", "production")

    response = client.post("/api/scheduler/refresh")

    assert response.status_code == 503
    assert scheduler.calls == 0
