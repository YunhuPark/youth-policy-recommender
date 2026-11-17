"""
Agent Orchestrator - 전체 에이전트 협업 조정자
청년 정책 추천 시스템의 5개 에이전트를 통합하여 완전한 추천 프로세스를 실행합니다.
"""

import time
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

# Database handler
from database.mongo_handler import get_mongodb_handler

# All agents
from agents.agent1_profile import Agent1
from agents.agent2_data import Agent2, PolicyFilter
from agents.agent3_matching import Agent3
from agents.agent4_gpt import Agent4
from agents.agent5_presentation import Agent5, FormattedResult


class ProcessingStep:
    """처리 단계 정보를 담는 클래스"""
    def __init__(self, step_name: str, agent_name: str):
        self.step_name = step_name
        self.agent_name = agent_name
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.success: bool = False
        self.error_message: Optional[str] = None
        self.result_data: Optional[Dict[str, Any]] = None

    def start(self):
        """단계 시작"""
        self.start_time = datetime.now()
        print(f"🚀 {self.step_name} 시작 ({self.agent_name})")

    def complete(self, result_data: Dict[str, Any]):
        """단계 완료"""
        self.end_time = datetime.now()
        self.success = True
        self.result_data = result_data
        duration = (self.end_time - self.start_time).total_seconds()
        print(f"✅ {self.step_name} 완료 ({duration:.2f}초)")

    def fail(self, error_message: str):
        """단계 실패"""
        self.end_time = datetime.now()
        self.success = False
        self.error_message = error_message
        duration = (self.end_time - self.start_time).total_seconds()
        print(f"❌ {self.step_name} 실패 ({duration:.2f}초): {error_message}")


class AgentOrchestrator:
    """
    Agent Orchestrator - 에이전트 조정자

    주요 기능:
    - 5개 에이전트의 순차적 실행 관리
    - 단계별 에러 처리 및 로깅
    - DB에 추천 이력 저장
    - 전체 프로세스 성능 모니터링
    """

    def __init__(self, use_database: bool = True):
        """Orchestrator 초기화"""
        self.orchestrator_name = "Youth Policy Recommendation Orchestrator"
        self.version = "1.0.0"
        self.use_database = use_database

        # MongoDB 핸들러 초기화
        self.mongo_handler = None
        if use_database:
            try:
                self.mongo_handler = get_mongodb_handler()
                if self.mongo_handler.is_connected:
                    print("✅ Orchestrator: MongoDB 연결 성공")
                else:
                    print("⚠️ Orchestrator: MongoDB 연결 실패, 로컬 모드로 실행")
                    self.use_database = False
            except Exception as e:
                print(f"⚠️ Orchestrator: MongoDB 초기화 실패 - {e}")
                self.use_database = False

        # 에이전트 인스턴스 생성
        try:
            self.agent1 = Agent1(use_database=self.use_database)
            self.agent2 = Agent2(use_database=self.use_database)
            self.agent3 = Agent3()
            self.agent4 = Agent4()
            self.agent5 = Agent5()
            print("✅ Orchestrator: 모든 에이전트 초기화 완료")
        except Exception as e:
            print(f"❌ Orchestrator: 에이전트 초기화 실패 - {e}")
            raise

        # 처리 단계 정의
        self.processing_steps = [
            ProcessingStep("프로필 수집 및 검증", "Agent 1"),
            ProcessingStep("정책 데이터 조회", "Agent 2"),
            ProcessingStep("매칭 및 점수 계산", "Agent 3"),
            ProcessingStep("GPT 설명 생성", "Agent 4"),
            ProcessingStep("결과 포맷팅", "Agent 5")
        ]

    def process_recommendation(self, user_input: Dict[str, Any],
                             min_score: float = 40.0,
                             max_results: int = 10) -> Dict[str, Any]:
        """
        전체 추천 프로세스 실행

        Args:
            user_input (Dict[str, Any]): 사용자 입력 데이터
            min_score (float): 최소 매칭 점수
            max_results (int): 최대 결과 수

        Returns:
            Dict[str, Any]: 최종 추천 결과
        """
        session_id = str(uuid.uuid4())
        start_time = datetime.now()

        print("\n" + "=" * 60)
        print("🎯 청년 정책 추천 시스템 - 전체 프로세스 시작")
        print(f"📋 세션 ID: {session_id}")
        print(f"⏰ 시작 시간: {start_time.isoformat()}")
        print("=" * 60)

        try:
            # Step 1: Agent 1 - 프로필 수집 및 검증
            step1 = self.processing_steps[0]
            step1.start()

            try:
                profile_result = self.agent1.collect_profile(user_input)
                if not profile_result.get("success"):
                    step1.fail(profile_result.get("error", "프로필 검증 실패"))
                    return self._create_error_response(
                        session_id, "프로필 검증에 실패했습니다.", step1.error_message
                    )

                user_profile = profile_result.get("profile_data", profile_result.get("profile", {}))
                profile_id = profile_result["profile_id"]
                step1.complete({"profile_id": profile_id, "profile": user_profile})

            except Exception as e:
                step1.fail(f"Agent1 오류: {str(e)}")
                return self._create_error_response(session_id, "프로필 처리 중 오류가 발생했습니다.", str(e))

            # Step 2: Agent 2 - 정책 데이터 조회
            step2 = self.processing_steps[1]
            step2.start()

            try:
                # 관심 분야 기반 필터 생성
                interest_filter = None
                if user_profile.get("interest"):
                    interest_filter = PolicyFilter(category=user_profile["interest"])

                policies_result = self.agent2.get_policies_from_db(interest_filter)

                if policies_result.get("success") and policies_result.get("policies"):
                    # DB에서 성공적으로 조회된 경우, Agent3용 형식으로 변환
                    policies_data = self._convert_policies_for_agent3(policies_result["policies"])
                else:
                    step2.fail(policies_result.get("error", "정책 정보 조회 실패"))
                    return self._create_error_response(
                        session_id, "정책 정보를 가져올 수 없습니다.", step2.error_message
                    )

                step2.complete({"policies_count": len(policies_data), "policies": policies_data})

            except Exception as e:
                step2.fail(f"Agent2 오류: {str(e)}")
                return self._create_error_response(session_id, "정책 조회 중 오류가 발생했습니다.", str(e))

            # Step 3: Agent 3 - 매칭 및 점수 계산
            step3 = self.processing_steps[2]
            step3.start()

            try:
                matching_results = self.agent3.match_policies(
                    user_profile, policies_data, min_score, max_results
                )

                if not matching_results:
                    step3.complete({"matched_count": 0, "matches": []})
                    return self._create_no_matches_response(session_id, user_profile)

                # 매칭 요약 생성
                matching_summary = self.agent3.get_matching_summary(user_profile, matching_results)

                # MatchingResult를 dict로 변환
                matches_dict = [result.model_dump() for result in matching_results]
                step3.complete({
                    "matched_count": len(matching_results),
                    "matches": matches_dict,
                    "summary": matching_summary
                })

            except Exception as e:
                step3.fail(f"Agent3 오류: {str(e)}")
                return self._create_error_response(session_id, "정책 매칭 중 오류가 발생했습니다.", str(e))

            # Step 4: Agent 4 - GPT 설명 생성
            step4 = self.processing_steps[3]
            step4.start()

            try:
                explained_policies = self.agent4.explain_all(matches_dict, user_profile)
                step4.complete({"explained_count": len(explained_policies)})

            except Exception as e:
                step4.fail(f"Agent4 오류: {str(e)}")
                # Agent4 실패 시에도 설명 없이 계속 진행
                explained_policies = matches_dict
                for policy in explained_policies:
                    policy["explanation"] = "설명을 생성할 수 없습니다."
                step4.complete({"explained_count": len(explained_policies)})
                print(f"⚠️ Agent4 실패, 설명 없이 계속 진행: {e}")

            # Step 5: Agent 5 - 결과 포맷팅
            step5 = self.processing_steps[4]
            step5.start()

            try:
                formatted_result = self.agent5.format_result(explained_policies, user_profile, matching_summary)
                step5.complete({"formatted_result": formatted_result.model_dump()})

            except Exception as e:
                step5.fail(f"Agent5 오류: {str(e)}")
                return self._create_error_response(session_id, "결과 포맷팅 중 오류가 발생했습니다.", str(e))

            # 최종 결과 생성
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()

            final_result = {
                "profile_id": profile_id,
                "session_id": session_id,
                "success": True,
                "message": "추천 프로세스가 성공적으로 완료되었습니다.",
                "processing_time": total_duration,
                "steps_summary": self._create_steps_summary(),
                "recommendation_result": formatted_result.model_dump(),
                "generated_at": end_time.isoformat()
            }

            # DB에 추천 이력 저장
            if self.use_database:
                try:
                    self._save_recommendation_history(session_id, user_profile, final_result)
                except Exception as e:
                    print(f"⚠️ 추천 이력 저장 실패: {e}")

            print("\n" + "=" * 60)
            print("🎉 추천 프로세스 완료!")
            print(f"⏱️ 총 처리 시간: {total_duration:.2f}초")
            print(f"📊 추천된 정책 수: {formatted_result.total_count}")
            print(f"📈 평균 매칭 점수: {formatted_result.avg_score}")
            print("=" * 60)

            # Issue the capability to this caller only, after history storage.
            final_result["access_token"] = profile_result["access_token"]
            return final_result

        except Exception as e:
            print(f"❌ 예상치 못한 오류 발생: {e}")
            return self._create_error_response(
                session_id, "시스템 오류가 발생했습니다.", str(e)
            )

    def _convert_policies_for_agent3(self, policies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Agent2의 정책 데이터를 Agent3용 형식으로 변환 (실제 DB 데이터 사용)"""
        converted_policies = []

        for policy in policies:
            # Agent3가 기대하는 필드로 변환 - 실제 DB 값 사용
            converted_policy = {
                "policy_id": policy.get("policy_id"),
                "title": policy.get("title"),
                "category": policy.get("category"),
                "target_age_min": policy.get("target_age_min"),  # None이면 Agent3에서 제한 없음으로 처리
                "target_age_max": policy.get("target_age_max"),  # None이면 Agent3에서 제한 없음으로 처리
                "target_regions": policy.get("target_regions", []),  # 빈 리스트면 Agent3에서 전국으로 처리
                "target_employment": policy.get("target_employment", []),  # 빈 리스트면 Agent3에서 제한 없음으로 처리
                "target_income_max": policy.get("target_income_max"),  # None이면 제한 없음
                "benefit": policy.get("benefit", ""),
                "budget_max": policy.get("budget_max"),
                "deadline": policy.get("deadline"),
                "application_url": policy.get("application_url", "")
            }
            converted_policies.append(converted_policy)

        return converted_policies



    def _create_steps_summary(self) -> List[Dict[str, Any]]:
        """처리 단계 요약 생성"""
        summary = []
        for step in self.processing_steps:
            step_info = {
                "step_name": step.step_name,
                "agent_name": step.agent_name,
                "success": step.success,
                "duration": 0.0
            }

            if step.start_time and step.end_time:
                step_info["duration"] = (step.end_time - step.start_time).total_seconds()

            if step.error_message:
                step_info["error"] = step.error_message

            summary.append(step_info)

        return summary

    def _create_error_response(self, session_id: str, message: str, detail: str) -> Dict[str, Any]:
        """에러 응답 생성"""
        return {
            "session_id": session_id,
            "success": False,
            "message": message,
            "error_detail": detail,
            "processing_time": 0.0,
            "steps_summary": self._create_steps_summary(),
            "recommendation_result": None,
            "generated_at": datetime.now().isoformat()
        }

    def _create_no_matches_response(self, session_id: str, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """매칭 결과 없음 응답 생성"""
        # Agent5로 빈 결과 포맷팅
        empty_result = self.agent5.format_result([], user_profile)

        return {
            "session_id": session_id,
            "success": True,
            "message": "조건에 맞는 정책을 찾지 못했습니다.",
            "processing_time": 0.0,
            "steps_summary": self._create_steps_summary(),
            "recommendation_result": empty_result.model_dump(),
            "generated_at": datetime.now().isoformat()
        }

    def _save_recommendation_history(self, session_id: str, user_profile: Dict[str, Any],
                                   result: Dict[str, Any]) -> bool:
        """추천 이력을 DB에 저장"""
        try:
            if not self.mongo_handler or not self.mongo_handler.is_connected:
                return False

            history_data = {
                "user_id": result["profile_id"],
                "session_id": session_id,
                "user_profile": user_profile,
                "recommendation_result": {key: value for key, value in result.items() if key != "access_token"},
                "created_at": datetime.now()
            }

            collection = self.mongo_handler.database["recommendation_history"]
            result = collection.insert_one(history_data)

            print(f"✅ 추천 이력 저장 완료: {result.inserted_id}")
            return True

        except Exception as e:
            print(f"⚠️ 추천 이력 저장 실패: {e}")
            return False

    def get_orchestrator_stats(self) -> Dict[str, Any]:
        """Orchestrator 상태 통계 반환"""
        return {
            "orchestrator_name": self.orchestrator_name,
            "version": self.version,
            "database_connected": self.use_database,
            "agents_status": {
                "agent1": "initialized",
                "agent2": "initialized",
                "agent3": "initialized",
                "agent4": "initialized",
                "agent5": "initialized"
            },
            "processing_steps": [step.step_name for step in self.processing_steps]
        }


# 테스트 코드
if __name__ == "__main__":
    print("🤖 Agent Orchestrator 테스트 시작...")
    print("=" * 50)

    # Orchestrator 초기화
    orchestrator = AgentOrchestrator(use_database=False)  # 테스트용으로 DB 비활성화

    # 테스트용 사용자 입력
    test_user_input = {
        "age": 25,
        "region": "서울",
        "income": 3000,
        "employment": "구직자",
        "interest": "일자리"
    }

    print("\n📊 Orchestrator 상태:")
    stats = orchestrator.get_orchestrator_stats()
    for key, value in stats.items():
        print(f"  - {key}: {value}")

    print("\n" + "=" * 50)
    print("🚀 전체 추천 프로세스 테스트")
    print("=" * 50)

    # 전체 프로세스 실행
    result = orchestrator.process_recommendation(test_user_input)

    print("\n" + "=" * 30)
    print("📋 최종 결과 요약")
    print("=" * 30)

    print(f"성공 여부: {result['success']}")
    print(f"메시지: {result['message']}")
    print(f"처리 시간: {result['processing_time']:.2f}초")
    print(f"세션 ID: {result['session_id']}")

    if result.get("recommendation_result"):
        rec_result = result["recommendation_result"]
        print(f"추천 정책 수: {rec_result.get('total_count', 0)}")
        print(f"평균 점수: {rec_result.get('avg_score', 0)}")

    print(f"\n📊 처리 단계별 결과:")
    for step in result.get("steps_summary", []):
        status = "✅" if step["success"] else "❌"
        print(f"{status} {step['step_name']} ({step['duration']:.2f}초)")

    print("\n✅ Orchestrator 테스트 완료!")
