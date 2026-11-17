import copy
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import main
from agents.agent1_profile import Agent1
from agents.agent4_gpt import Agent4

PROFILE = {"age": 25, "region": "서울", "income": 3000, "employment": "학생"}


class Store:
    is_connected = True
    def __init__(self):
        self.profiles = {}

    def save_user_profile(self, data):
        self.profiles[data["profile_id"]] = dict(data, is_active=True)
        return {"success": True}

    def get_user_profile(self, profile_id):
        profile = self.profiles.get(profile_id)
        return {"success": bool(profile), "profile": copy.deepcopy(profile)}

    def update_user_profile(self, profile_id, data):
        self.profiles[profile_id].update(data)
        return {"success": True}

    def get_collection(self, name):
        store = self
        class Collection:
            def find_one(self, query):
                if name == "policies":
                    return {"policy_id": "p1", "title": "Canonical policy"} if query["policy_id"] == "p1" else None
                return store.profiles.get(query["profile_id"])
        return Collection()


@pytest.fixture
def client(monkeypatch, tmp_path):
    store = Store()
    monkeypatch.setattr(main, "mongo_handler", store)
    monkeypatch.setattr("agents.agent1_profile.get_mongodb_handler", lambda: store)
    monkeypatch.setenv("AI_BUDGET_DB", str(tmp_path / "budget.db"))
    return TestClient(main.app), store


def test_profile_id_is_not_a_read_capability(client):
    api, store = client
    owner = api.post("/api/profile", json=PROFILE).json()
    response = api.get("/api/profile/" + owner["profile_id"])
    assert response.status_code == 401


def test_capability_is_profile_bound_and_updates_work(client):
    api, store = client
    a = api.post("/api/profile", json=PROFILE).json()
    b = api.post("/api/profile", json=PROFILE).json()
    assert "access_token" in a
    headers = {"Authorization": "Bearer " + a["access_token"]}
    assert api.get("/api/profile/" + b["profile_id"], headers=headers).status_code == 403
    response = api.put("/api/profile/" + a["profile_id"], headers=headers, json=dict(PROFILE, income=2000))
    assert response.status_code == 200
    result = api.get("/api/profile/" + a["profile_id"], headers=headers)
    assert result.json()["profile"]["income"] == 2000
    assert "access_token_hash" not in result.json()["profile"]
    assert a["access_token"] not in str(store.profiles)


def test_explain_rejects_excessive_fanout_before_model(client, monkeypatch):
    api, _ = client
    calls = []
    monkeypatch.setattr(Agent4, "explain_all", lambda self, policies, profile: calls.append(policies) or [])
    result = api.post("/api/explain", json=dict(PROFILE, policies=[{"title": "test"}] * 11))
    assert result.status_code == 422
    assert calls == []


def test_explain_global_daily_budget_survives_new_clients(client, monkeypatch):
    api, _ = client
    monkeypatch.setenv("AI_DAILY_POLICY_LIMIT", "1")
    monkeypatch.setattr(Agent4, "explain_all", lambda *args: [])
    payload = dict(PROFILE, policies=[{"policy_id": "p1"}])
    assert api.post("/api/explain", json=payload).status_code == 200
    other = TestClient(main.app)
    assert other.post("/api/explain", json=payload).status_code == 429


def test_expired_revoked_and_legacy_capabilities_fail_closed(client):
    api, store = client
    owner = api.post("/api/profile", json=PROFILE).json()
    profile_id = owner["profile_id"]
    headers = {"Authorization": "Bearer " + owner["access_token"]}
    store.profiles[profile_id]["access_token_expires_at"] = "2000-01-01T00:00:00+00:00"
    assert api.get("/api/profile/" + profile_id, headers=headers).status_code == 403
    assert api.get("/api/user/" + profile_id + "/history").status_code == 401
    store.profiles[profile_id].pop("access_token_hash")
    assert api.put("/api/profile/" + profile_id, headers=headers, json=PROFILE).status_code == 403


def test_explain_uses_server_policy_and_rejects_unknown_ids(client, monkeypatch):
    api, _ = client
    seen = []
    monkeypatch.setattr(Agent4, "explain_all", lambda self, policies, profile: seen.extend(policies) or [])
    response = api.post("/api/explain", json=dict(PROFILE, policies=[{"policy_id": "p1", "title": "attacker prompt"}]))
    assert response.status_code == 200
    assert seen[0]["title"] == "Canonical policy"
    assert api.post("/api/explain", json=dict(PROFILE, policies=[{"policy_id": "missing"}])).status_code == 404


def test_daily_budget_is_atomic_across_concurrent_connections(client, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from core.ai_budget import reserve_policy_calls
    from fastapi import HTTPException
    monkeypatch.setenv("AI_DAILY_POLICY_LIMIT", "3")
    def reserve(i):
        try:
            reserve_policy_calls(1, str(i))
            return True
        except HTTPException as error:
            assert error.status_code == 429
            return False
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(reserve, range(12))) == 3


def test_history_storage_never_persists_orchestrator_capability(client):
    from orchestrator import AgentOrchestrator
    saved = []
    writer = SimpleNamespace(insert_one=lambda data: saved.append(data) or SimpleNamespace(inserted_id='synthetic'))
    orchestrator = object.__new__(AgentOrchestrator)
    orchestrator.mongo_handler = SimpleNamespace(is_connected=True, database={"recommendation_history": writer})
    assert orchestrator._save_recommendation_history("session", PROFILE, {
        "profile_id": "owner", "access_token": "private", "success": True,
    })
    assert saved[0]["user_id"] == "owner"
    assert "private" not in str(saved)


def test_normal_orchestrator_returns_profile_capability_usable_for_update(client, monkeypatch):
    import orchestrator
    from agents.agent2_data import Agent2
    api, store = client
    monkeypatch.setattr(orchestrator, "get_mongodb_handler", lambda: store)
    monkeypatch.setattr("agents.agent2_data.get_mongodb_handler", lambda: store)
    monkeypatch.setattr(Agent2, "get_policies_from_db", lambda *a, **k: {"success": True, "policies": [{
        "policy_id": "p1", "title": "Canonical policy", "category": "일자리", "benefit": "지원금",
        "target_age_min": 15, "target_age_max": 39, "target_regions": ["전국"],
        "target_employment": ["학생"], "deadline": "상시", "budget_max": 1000,
    }]})
    response = api.post("/api/orchestrator", json=dict(PROFILE, max_results=10, min_score=0))
    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True, result
    assert result["recommendation_result"]["recommendations"]
    headers = {"Authorization": "Bearer " + result["access_token"]}
    assert api.get("/api/profile/" + result["profile_id"], headers=headers).status_code == 200
    assert api.put("/api/profile/" + result["profile_id"], headers=headers, json=dict(PROFILE, income=2000)).status_code == 200
