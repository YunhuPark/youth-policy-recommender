"""Matching requires explicit policy data, without a database or network."""
from agents.agent3_matching import Agent3


def test_matching():
    profile = {"age": 26, "region": "서울", "employment": "학생", "income": 0}
    policies = [{"policy_id": "study", "title": "청년 학업 지원", "category": "교육",
                 "target_age_min": 15, "target_age_max": 39, "target_regions": ["전국"],
                 "target_employment": ["학생"], "benefit": "학비 지원", "deadline": "상시"}]
    results = Agent3().match_policies(profile, policies, min_score=0, max_results=5)
    assert len(results) == 1
    assert results[0].policy_id == "study"
    assert 0 < results[0].score <= 100
    assert results[0].match_reasons
