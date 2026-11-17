"""
청년 정책 추천 시스템 - Agent 테스트
모든 Agent의 기능을 검증하는 종합 테스트 스위트
"""

import pytest
import sys
import os
from datetime import datetime
import copy

# 테스트를 위한 경로 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.agent1_profile import Agent1
from agents.agent2_data import Agent2, PolicyFilter
from agents.agent3_matching import Agent3
from agents.agent4_gpt import Agent4
from agents.agent5_presentation import Agent5
from orchestrator import AgentOrchestrator



# Exercise real agent/orchestrator logic using a deterministic repository boundary.
# No production code returns fabricated policy data when its DB is unavailable.
class PolicyRepository:
    def get_all_policies(self):
        policies = copy.deepcopy([
            {"policy_id": "startup-fixture", "title": "청년 창업 지원", "category": "창업",
             "target_age_min": 15, "target_age_max": 39, "target_regions": ["전국"],
             "target_employment": [], "target_income_max": 10000,
             "benefit": "최대 5천만원 지원", "budget_max": 5000,
             "deadline": f"{datetime.now().year + 1}년 12월 31일"},
            {"policy_id": "housing-fixture", "title": "청년 주거 지원", "category": "주거",
             "target_age_min": 15, "target_age_max": 39, "target_regions": ["전국"],
             "target_employment": [], "benefit": "주거 지원", "budget_max": 1000,
             "deadline": "상시"}
        ])
        for category in ["금융", "교육", "문화", "복지", "일자리"]:
            policies.append(dict(policies[0], policy_id="fixture-" + category,
                                 title="청년 " + category + " 지원", category=category))
        return {"success": True, "policies": policies}

    def get_policies_by_category(self, category, active_only=True):
        return {"success": True, "policies": [p for p in self.get_all_policies()["policies"]
                                               if p["category"] == category]}


def format_current(agent, profile, recommendations, max_results=10):
    return agent.format_result(recommendations[:max_results], profile).model_dump()


class TestAgent1Profile:
    """Agent 1 (프로필 수집 및 검증) 테스트"""

    def setup_method(self):
        """각 테스트 전에 실행되는 설정"""
        self.agent = Agent1(use_database=False)

    def test_valid_profile_collection(self):
        """정상적인 프로필 입력 테스트"""
        user_input = {
            "age": 28,
            "region": "서울",
            "income": 3000,
            "employment": "재직자",
            "interest": "창업"
        }

        result = self.agent.collect_profile(user_input)

        assert result["success"] is True
        assert "profile_id" in result
        assert result["profile_data"]["age"] == 28
        assert result["profile_data"]["region"] == "서울"
        assert result["profile_data"]["income"] == 3000
        assert result["profile_data"]["employment"] == "재직자"
        assert result["profile_data"]["interest"] == "창업"

    def test_age_range_validation(self):
        """나이 범위 검증 테스트"""
        # 최소 나이 미만
        user_input_under = {
            "age": 14,
            "region": "서울",
            "income": 3000,
            "employment": "재직자"
        }
        result = self.agent.collect_profile(user_input_under)
        assert result["success"] is False
        assert "age" in result["error"]

        # 최대 나이 초과
        user_input_over = {
            "age": 40,
            "region": "서울",
            "income": 3000,
            "employment": "재직자"
        }
        result = self.agent.collect_profile(user_input_over)
        assert result["success"] is False
        assert "age" in result["error"]

    def test_missing_required_fields(self):
        """필수 필드 누락 테스트"""
        incomplete_inputs = [
            {"region": "서울", "income": 3000, "employment": "재직자"},  # age 누락
            {"age": 28, "income": 3000, "employment": "재직자"},  # region 누락
            {"age": 28, "region": "서울", "employment": "재직자"},  # income 누락
            {"age": 28, "region": "서울", "income": 3000}  # employment 누락
        ]

        for incomplete_input in incomplete_inputs:
            result = self.agent.collect_profile(incomplete_input)
            assert result["success"] is False
            assert "필수" in result["error"]

    def test_negative_income(self):
        """음수 소득 검증 테스트"""
        user_input = {
            "age": 28,
            "region": "서울",
            "income": -1000,
            "employment": "재직자"
        }
        result = self.agent.collect_profile(user_input)
        assert result["success"] is False
        assert "income" in result["error"]

    def test_empty_string_validation(self):
        """빈 문자열 검증 테스트"""
        user_input = {
            "age": 28,
            "region": "",
            "income": 3000,
            "employment": "재직자"
        }
        result = self.agent.collect_profile(user_input)
        assert result["success"] is False

    def test_valid_employment_types(self):
        """다양한 고용 상태 유형 테스트"""
        valid_employments = ["재직자", "구직자", "자영업", "무직", "학생"]

        for employment in valid_employments:
            user_input = {
                "age": 28,
                "region": "서울",
                "income": 3000,
                "employment": employment
            }
            result = self.agent.collect_profile(user_input)
            assert result["success"] is True
            assert result["profile_data"]["employment"] == employment


class TestAgent2Data:
    """Agent 2 (정책 데이터 관리) 테스트"""

    def setup_method(self):
        """각 테스트 전에 실행되는 설정"""
        self.agent = Agent2(use_database=False)
        self.agent.db_handler = PolicyRepository()

    def test_get_policies_without_filter(self):
        """필터 없이 전체 정책 조회 테스트"""
        result = self.agent.get_policies_from_db()

        assert result["success"] is True
        assert "policies" in result
        assert len(result["policies"]) > 0

        # 첫 번째 정책의 구조 확인
        first_policy = result["policies"][0]
        required_fields = ["policy_id", "title", "category"]
        for field in required_fields:
            assert field in first_policy

    def test_get_policies_with_category_filter(self):
        """카테고리 필터링 테스트"""
        filter_condition = PolicyFilter(category="창업")
        result = self.agent.get_policies_from_db(filter_condition)

        assert result["success"] is True
        # 더미 데이터에서 창업 카테고리 정책이 있는지 확인
        policies = result["policies"]
        if policies:
            startup_policies = [p for p in policies if p.get("category") == "창업"]
            assert len(startup_policies) > 0

    def test_policy_data_structure(self):
        """정책 데이터 구조 검증"""
        result = self.agent.get_policies_from_db()

        if result["success"] and result["policies"]:
            policy = result["policies"][0]

            # 필수 필드 확인
            assert isinstance(policy.get("policy_id"), str)
            assert isinstance(policy.get("title"), str)
            assert isinstance(policy.get("category"), str)

            # 선택적 필드 타입 확인
            if "target_age_min" in policy:
                assert isinstance(policy["target_age_min"], (int, type(None)))
            if "target_age_max" in policy:
                assert isinstance(policy["target_age_max"], (int, type(None)))


class TestAgent3Matching:
    """Agent 3 (정책 매칭) 테스트"""

    def setup_method(self):
        """각 테스트 전에 실행되는 설정"""
        self.agent = Agent3()
        self.sample_policies = [
            {
                "policy_id": "JOB_001",
                "title": "청년 창업 지원금",
                "category": "창업",
                "target_age_min": 18,
                "target_age_max": 39,
                "target_regions": ["전국"],
                "target_employment": ["구직자", "자영업"],
                "target_income_max": 10000,
                "benefit": "최대 5천만원 지원",
                "budget_max": 5000,
                "deadline": f"{datetime.now().year + 1}년 12월 31일",
                "application_url": "https://startup.go.kr"
            },
            {
                "policy_id": "FIN_001",
                "title": "청년희망적금",
                "category": "금융",
                "target_age_min": 19,
                "target_age_max": 34,
                "target_regions": ["전국"],
                "target_employment": ["재직자", "구직자"],
                "target_income_max": 3600,
                "benefit": "월 10만원 적립시 정부지원금 10만원",
                "budget_max": 240,
                "deadline": f"{datetime.now().year + 1}년 12월 31일",
                "application_url": "https://finlife.or.kr"
            }
        ]

    def test_perfect_match_scenario(self):
        """완벽한 매칭 시나리오 테스트"""
        user_profile = {
            "age": 25,
            "region": "서울",
            "income": 3000,
            "employment": "재직자",
            "interest": "금융"
        }

        results = self.agent.match_policies(
            user_profile,
            self.sample_policies,
            min_score=0.0,
            max_results=10
        )

        assert len(results) > 0

        # 금융 카테고리 정책이 높은 점수를 받았는지 확인
        fin_policy = next((r for r in results if r.policy_id == "FIN_001"), None)
        assert fin_policy is not None
        assert fin_policy.score > 50.0  # 적정 점수 이상

    def test_age_mismatch_scenario(self):
        """나이 조건 불일치 시나리오 테스트"""
        user_profile = {
            "age": 45,  # 모든 정책 나이 범위 초과
            "region": "서울",
            "income": 3000,
            "employment": "재직자"
        }

        results = self.agent.match_policies(
            user_profile,
            self.sample_policies,
            min_score=40.0,
            max_results=10
        )

        # 나이 조건 불일치로 낮은 점수 또는 결과 없음
        if results:
            for result in results:
                assert result.score < 70.0  # 나이 불일치로 인한 낮은 점수

    def test_score_calculation_accuracy(self):
        """점수 계산 정확성 테스트"""
        user_profile = {
            "age": 25,
            "region": "서울",
            "income": 3000,
            "employment": "재직자"
        }

        results = self.agent.match_policies(
            user_profile,
            self.sample_policies,
            min_score=0.0,
            max_results=10
        )

        for result in results:
            # 점수가 유효한 범위 내에 있는지 확인
            assert 0.0 <= result.score <= 100.0

            # 매칭 이유가 제공되는지 확인
            assert isinstance(result.match_reasons, list)
            assert len(result.match_reasons) > 0

    def test_min_score_filtering(self):
        """최소 점수 필터링 테스트"""
        user_profile = {
            "age": 25,
            "region": "서울",
            "income": 3000,
            "employment": "재직자"
        }

        high_min_score = 90.0
        results = self.agent.match_policies(
            user_profile,
            self.sample_policies,
            min_score=high_min_score,
            max_results=10
        )

        # 높은 최소 점수로 인해 결과가 적을 것으로 예상
        for result in results:
            assert result.score >= high_min_score

    def test_max_results_limitation(self):
        """최대 결과 수 제한 테스트"""
        user_profile = {
            "age": 25,
            "region": "서울",
            "income": 3000,
            "employment": "재직자"
        }

        max_results = 1
        results = self.agent.match_policies(
            user_profile,
            self.sample_policies,
            min_score=0.0,
            max_results=max_results
        )

        assert len(results) <= max_results

    def test_matching_summary_generation(self):
        """매칭 요약 생성 테스트"""
        user_profile = {
            "age": 25,
            "region": "서울",
            "income": 3000,
            "employment": "재직자"
        }

        results = self.agent.match_policies(
            user_profile,
            self.sample_policies,
            min_score=0.0,
            max_results=10
        )

        summary = self.agent.get_matching_summary(user_profile, results)

        assert "success" in summary
        assert "message" in summary
        assert "user_profile_summary" in summary
        assert "total_matches" in summary
        assert summary["total_matches"] == len(results)


class TestAgent4GPT:
    """Agent 4 (GPT 설명 생성) 테스트"""

    def setup_method(self):
        """각 테스트 전에 실행되는 설정"""
        self.agent = Agent4()
        self.sample_user_profile = {
            "age": 28,
            "region": "서울",
            "income": 3000,
            "employment": "재직자",
            "interest": "창업"
        }
        self.sample_policies = [
            {
                "policy_id": "JOB_001",
                "title": "청년 창업 지원금",
                "category": "창업",
                "score": 89.5,
                "match_reasons": ["연령 조건 만족", "창업 관심도 일치"],
                "benefit_summary": "최대 5천만원 지원",
                "deadline": f"{datetime.now().year + 1}년 12월 31일"
            }
        ]

    def test_single_policy_explanation(self):
        """단일 정책 설명 생성 테스트"""
        result = self.agent.generate_explanation(
            self.sample_policies[0], self.sample_user_profile,
            self.sample_policies[0]["score"], self.sample_policies[0]["match_reasons"]
        ).model_dump()

        assert "explanation" in result
        assert isinstance(result["explanation"], str)
        assert len(result["explanation"]) > 0

        # Fallback 모드에서도 기본 설명이 생성되는지 확인
        assert "창업" in result["explanation"] or "정책" in result["explanation"]

    def test_multiple_policies_explanation(self):
        """다중 정책 설명 생성 테스트"""
        policies = self.sample_policies * 2  # 정책 2개로 확장

        results = self.agent.explain_all(policies, self.sample_user_profile)

        assert isinstance(results, list)
        assert len(results) == len(policies)

        for result in results:
            assert "explanation" in result
            assert isinstance(result["explanation"], str)

    def test_explanation_contains_user_context(self):
        """설명에 사용자 맥락이 포함되는지 테스트"""
        result = self.agent.generate_explanation(
            self.sample_policies[0], self.sample_user_profile,
            self.sample_policies[0]["score"], self.sample_policies[0]["match_reasons"]
        ).model_dump()

        explanation = result["explanation"].lower()

        # 사용자 정보 관련 키워드가 포함되었는지 확인
        user_keywords = ["28세", "재직자", "창업", "서울"]
        found_keywords = [keyword for keyword in user_keywords if keyword.lower() in explanation]

        # 적어도 하나의 사용자 관련 키워드가 포함되어야 함
        assert len(found_keywords) > 0 or "fallback" in explanation.lower()


class TestAgent5Presentation:
    """Agent 5 (결과 정리) 테스트"""

    def setup_method(self):
        """각 테스트 전에 실행되는 설정"""
        self.agent = Agent5()
        self.sample_user_profile = {
            "age": 28,
            "region": "서울",
            "income": 3000,
            "employment": "재직자",
            "interest": "창업"
        }
        self.sample_recommendations = [
            {
                "policy_id": "JOB_001",
                "title": "청년 창업 지원금",
                "category": "창업",
                "score": 89.5,
                "match_reasons": ["연령 조건 만족", "창업 관심도 일치"],
                "benefit_summary": "최대 5천만원 지원",
                "deadline": f"{datetime.now().year + 1}년 12월 31일",
                "explanation": "회원님의 창업 관심도와 현재 조건에 매우 적합한 정책입니다."
            }
        ]

    def test_format_recommendations_basic(self):
        """기본 추천 결과 포맷팅 테스트"""
        result = format_current(self.agent,
            self.sample_user_profile,
            self.sample_recommendations,
            max_results=5
        )

        assert result["success"] is True
        assert "user_profile_summary" in result
        assert "total_count" in result
        assert "recommendations" in result
        assert len(result["recommendations"]) <= 5

    def test_user_profile_summary_generation(self):
        """사용자 프로필 요약 생성 테스트"""
        result = format_current(self.agent,
            self.sample_user_profile,
            self.sample_recommendations
        )

        profile_summary = result["user_profile_summary"]

        # 주요 정보가 포함되었는지 확인
        assert "28세" in profile_summary
        assert "서울" in profile_summary
        assert "재직자" in profile_summary
        assert "창업" in profile_summary

    def test_score_grading_system(self):
        """점수 등급 시스템 테스트"""
        test_recommendations = [
            {**self.sample_recommendations[0], "score": 95.0},  # S등급 예상
            {**self.sample_recommendations[0], "score": 85.0, "policy_id": "TEST_2"},  # A등급 예상
            {**self.sample_recommendations[0], "score": 75.0, "policy_id": "TEST_3"},  # B등급 예상
            {**self.sample_recommendations[0], "score": 65.0, "policy_id": "TEST_4"},  # C등급 예상
        ]

        result = format_current(self.agent,
            self.sample_user_profile,
            test_recommendations
        )

        recommendations = result["recommendations"]

        for rec in recommendations:
            assert "score_grade" in rec
            score_grade = rec["score_grade"]
            score = rec["score"]

            # 점수에 따른 등급이 올바른지 확인
            if score >= 90:
                assert score_grade == "S"
            elif score >= 80:
                assert score_grade == "A"
            elif score >= 70:
                assert score_grade == "B"
            elif score >= 60:
                assert score_grade == "C"

    def test_comparison_table_generation(self):
        """비교 테이블 생성 테스트"""
        result = format_current(self.agent,
            self.sample_user_profile,
            self.sample_recommendations
        )

        assert "comparison_table" in result
        table = result["comparison_table"]

        assert "headers" in table
        assert "rows" in table
        assert isinstance(table["headers"], list)
        assert isinstance(table["rows"], list)

        # 헤더가 올바른지 확인
        expected_headers = ["정책명", "점수", "혜택", "주관기관", "마감일"]
        for header in expected_headers:
            assert header in table["headers"]


class TestOrchestrator:
    """Orchestrator (전체 통합) 테스트"""

    def setup_method(self):
        """각 테스트 전에 실행되는 설정"""
        self.orchestrator = AgentOrchestrator(use_database=False)
        self.orchestrator.agent2.db_handler = PolicyRepository()

    def test_complete_workflow_success(self):
        """완전한 워크플로우 성공 시나리오 테스트"""
        user_input = {
            "age": 28,
            "region": "서울",
            "income": 3000,
            "employment": "재직자",
            "interest": "창업"
        }

        result = self.orchestrator.process_recommendation(
            user_input,
            min_score=40.0,
            max_results=3
        )

        assert result["success"] is True
        assert "session_id" in result
        assert "processing_time" in result
        assert "steps_summary" in result
        assert "recommendation_result" in result

        # 각 단계가 성공했는지 확인
        steps = result["steps_summary"]
        assert len(steps) == 5  # 5개 Agent

        for step in steps:
            assert step["success"] is True
            assert "duration" in step

    def test_workflow_with_invalid_profile(self):
        """잘못된 프로필로 워크플로우 실행 테스트"""
        invalid_user_input = {
            "age": 14,  # 나이 조건 불만족
            "region": "서울",
            "income": 3000,
            "employment": "재직자"
        }

        result = self.orchestrator.process_recommendation(
            invalid_user_input,
            min_score=40.0,
            max_results=3
        )

        assert result["success"] is False
        assert "error_detail" in result

    def test_workflow_performance(self):
        """워크플로우 성능 테스트"""
        user_input = {
            "age": 28,
            "region": "서울",
            "income": 3000,
            "employment": "재직자"
        }

        start_time = datetime.now()
        result = self.orchestrator.process_recommendation(
            user_input,
            min_score=40.0,
            max_results=5
        )
        end_time = datetime.now()

        execution_time = (end_time - start_time).total_seconds()

        # 전체 실행 시간이 합리적인 범위 내에 있는지 확인 (10초 미만)
        assert execution_time < 10.0
        assert result["success"] is True
        # The API rounds sub-centisecond offline work to zero.
        assert 0 <= result["processing_time"] <= execution_time + 0.01

    def test_workflow_with_different_profiles(self):
        """다양한 프로필로 워크플로우 테스트"""
        test_profiles = [
            {
                "age": 22,
                "region": "부산",
                "income": 2000,
                "employment": "구직자",
                "interest": "주거"
            },
            {
                "age": 35,
                "region": "대구",
                "income": 5000,
                "employment": "자영업",
                "interest": "금융"
            },
            {
                "age": 30,
                "region": "인천",
                "income": 4000,
                "employment": "재직자",
                "interest": "문화"
            }
        ]

        for profile in test_profiles:
            result = self.orchestrator.process_recommendation(
                profile,
                min_score=30.0,
                max_results=3
            )

            assert result["success"] is True
            assert len(result["recommendation_result"]["recommendations"]) <= 3

    def test_session_id_uniqueness(self):
        """세션 ID 고유성 테스트"""
        user_input = {
            "age": 28,
            "region": "서울",
            "income": 3000,
            "employment": "재직자"
        }

        session_ids = []

        for _ in range(3):
            result = self.orchestrator.process_recommendation(user_input)
            assert result["success"] is True
            session_ids.append(result["session_id"])

        # 모든 세션 ID가 고유한지 확인
        assert len(session_ids) == len(set(session_ids))


# 테스트 유틸리티 함수들
def test_environment_variables(monkeypatch):
    """Offline mode must work without workstation credentials and report no DB save."""
    monkeypatch.delenv("MONGODB_URI", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    agent = Agent1(use_database=False)
    result = agent.collect_profile({"age": 25, "region": "서울", "income": 0, "employment": "학생"})
    assert result["success"] is True
    assert result["database_saved"] is False
    assert agent.db_handler is None


def test_import_all_modules():
    """모든 주요 모듈 임포트 테스트"""
    try:
        import agents.agent1_profile
        import agents.agent2_data
        import agents.agent3_matching
        import agents.agent4_gpt
        import agents.agent5_presentation
        import database.mongo_handler
        import orchestrator
        print("✅ 모든 모듈 임포트 성공")
    except ImportError as e:
        pytest.fail(f"모듈 임포트 실패: {e}")


if __name__ == "__main__":
    print("🚀 청년 정책 추천 시스템 - Agent 테스트 시작")

    # 기본 테스트 실행
    pytest.main([
        __file__,
        "-v",  # 상세 출력
        "--tb=short",  # 간단한 traceback
        "-x"  # 첫 번째 실패 시 중단
    ])