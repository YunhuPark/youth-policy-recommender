"""
Agent 4: GPT-4 정책 설명 생성 에이전트
청년 정책 추천 시스템의 네 번째 에이전트로, 매칭된 정책에 대한 자연어 설명을 생성합니다.
"""

import os
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = False  # Disabled due to timeout issues
except ImportError:
    OPENAI_AVAILABLE = False

# 환경 변수 로드
load_dotenv()


class PolicyExplanation(BaseModel):
    """
    정책 설명 모델
    Agent4의 GPT 생성 설명을 담는 데이터 모델
    """
    policy_id: str = Field(..., description="정책 고유 ID")
    explanation: str = Field(..., description="GPT 생성 설명")
    generated_at: str = Field(..., description="설명 생성 시간")
    gpt_model: str = Field(..., description="사용된 GPT 모델")

    class Config:
        json_schema_extra = {
            "example": {
                "policy_id": "JOB_001",
                "explanation": "25세 구직자인 회원님께 이 정책을 추천드리는 이유는 나이 조건에 완벽히 맞고, 최대 1200만원의 높은 혜택을 받을 수 있기 때문입니다. 2년 동안 꾸준히 근무하시면 목돈을 마련할 수 있어 향후 창업이나 결혼 자금으로 활용하기 좋습니다. 신청 시에는 건강보험 가입 이력을 미리 확인해두세요!",
                "generated_at": "2024-01-05T10:30:00",
                "gpt_model": "gpt-4"
            }
        }


class Agent4:
    """
    Agent 4: GPT-4 정책 설명 생성 에이전트

    주요 기능:
    - OpenAI GPT-4 API를 활용한 자연어 설명 생성
    - 사용자 맞춤형 정책 해석 및 추천 이유 설명
    - 신청 시 주의사항 및 활용 팁 제공
    - 친근하고 이해하기 쉬운 톤앤매너 적용
    """

    def __init__(self, model: str = "gpt-4", temperature: float = 0.7):
        """Agent4 초기화"""
        self.agent_name = "Policy Explanation Agent"
        self.agent_version = "1.0.0"
        self.model = model
        self.temperature = temperature
        self.max_tokens = 300

        # OpenAI 클라이언트 초기화
        self.client = None
        self.is_available = False

        if OPENAI_AVAILABLE:
            try:
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    # OpenAI 클라이언트 초기화 (버전 호환성을 위해 간소화)
                    self.client = OpenAI(api_key=api_key, timeout=15.0, max_retries=0)
                    self.is_available = True
                    print(f"✅ Agent4: OpenAI 클라이언트 초기화 성공 (모델: {self.model})")
                else:
                    print("⚠️ Agent4: OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
                    print("   Fallback 모드로 실행됩니다.")
            except Exception as e:
                print(f"⚠️ Agent4: OpenAI 클라이언트 초기화 실패 - {e}")
                print("   Fallback 모드로 실행됩니다.")
        else:
            print("⚠️ Agent4: openai 패키지가 설치되지 않았습니다.")
            print("   pip install openai 명령으로 설치 후 사용하세요.")

        # 시스템 프롬프트 설정
        self.system_prompt = """당신은 청년 정책 전문 상담사입니다.
청년들에게 맞춤형 정책을 친절하고 이해하기 쉽게 설명하는 것이 주특기입니다.

설명 시 반드시 포함해야 할 요소:
1. 왜 이 정책이 해당 사용자에게 추천되는지 (조건 부합, 혜택 크기 등)
2. 이 정책의 핵심 혜택과 장점
3. 신청 시 주의사항이나 팁

톤앤매너:
- 친근하고 격려하는 말투
- 전문용어는 쉽게 풀어서 설명
- 구체적이고 실용적인 정보 제공
- 200자 이내로 간결하게"""

    def generate_explanation(self, policy: Dict[str, Any], user_profile: Dict[str, Any],
                           score: float, match_reasons: List[str] = None) -> PolicyExplanation:
        """
        단일 정책에 대한 GPT 설명 생성

        Args:
            policy (Dict[str, Any]): 정책 정보
            user_profile (Dict[str, Any]): 사용자 프로필
            score (float): 매칭 점수
            match_reasons (List[str], optional): 매칭 이유 목록

        Returns:
            PolicyExplanation: 생성된 설명 정보
        """
        try:
            if not self.is_available:
                return self._get_fallback_explanation(policy, user_profile, score)

            # 사용자 프롬프트 구성
            user_prompt = self._build_user_prompt(policy, user_profile, score, match_reasons)

            # GPT API 호출
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )

            explanation_text = response.choices[0].message.content.strip()

            # 결과 반환
            from datetime import datetime
            return PolicyExplanation(
                policy_id=policy.get("policy_id", "unknown"),
                explanation=explanation_text,
                generated_at=datetime.now().isoformat(),
                gpt_model=self.model
            )

        except openai.RateLimitError as e:
            print(f"⚠️ Agent4: API 사용량 한도 초과 - {e}")
            time.sleep(1)  # 잠시 대기 후 재시도
            return self._get_fallback_explanation(policy, user_profile, score)

        except openai.APIError as e:
            print(f"⚠️ Agent4: OpenAI API 오류 - {e}")
            return self._get_fallback_explanation(policy, user_profile, score)

        except Exception as e:
            print(f"⚠️ Agent4: 설명 생성 중 오류 - {e}")
            return self._get_fallback_explanation(policy, user_profile, score)

    def _build_user_prompt(self, policy: Dict[str, Any], user_profile: Dict[str, Any],
                          score: float, match_reasons: List[str] = None) -> str:
        """사용자 프롬프트 구성"""

        # 사용자 정보 정리
        age = user_profile.get("age", "미상")
        region = user_profile.get("region", "미상")
        income = user_profile.get("income", 0)
        employment = user_profile.get("employment", "미상")
        interest = user_profile.get("interest", "")

        # 정책 정보 정리
        title = policy.get("title", "정책명 미상")
        category = policy.get("category", "분야 미상")
        benefit = policy.get("benefit", policy.get("benefit_summary", "혜택 정보 없음"))
        deadline = policy.get("deadline", "신청 기간 미상")

        # 매칭 이유 정리
        reasons_text = ""
        if match_reasons:
            reasons_text = f"매칭 이유: {', '.join(match_reasons[:3])}"

        prompt = f"""다음 청년에게 정책을 추천하여 설명해주세요:

📋 사용자 정보:
- 나이: {age}세
- 거주지역: {region}
- 연소득: {income:,}만원
- 취업상태: {employment}
- 관심분야: {interest if interest else '없음'}

📋 추천 정책:
- 정책명: {title}
- 분야: {category}
- 혜택: {benefit}
- 신청 기간: {deadline}
- 적합도 점수: {score}점/100점
{reasons_text}

이 사용자에게 이 정책이 왜 좋은지, 어떤 혜택을 받을 수 있는지, 신청할 때 주의할 점은 무엇인지 200자 이내로 친근하게 설명해주세요."""

        return prompt

    def _get_fallback_explanation(self, policy: Dict[str, Any], user_profile: Dict[str, Any],
                                score: float) -> PolicyExplanation:
        """GPT 사용 불가능 시 기본 설명 생성"""

        title = policy.get("title", "이 정책")
        benefit = policy.get("benefit", policy.get("benefit_summary", "다양한 혜택"))
        age = user_profile.get("age", 0)
        employment = user_profile.get("employment", "")

        # 간단한 템플릿 기반 설명
        fallback_text = f"{age}세 {employment} 회원님의 조건에 맞는 '{title}'을(를) 추천드립니다. "

        if score >= 90:
            fallback_text += f"매칭도가 {score}점으로 매우 높아 혜택을 충분히 받으실 수 있습니다. "
        elif score >= 70:
            fallback_text += f"매칭도가 {score}점으로 좋은 조건입니다. "
        else:
            fallback_text += f"기본 조건은 만족하지만 일부 조건에서 차이가 있습니다. "

        fallback_text += f"{benefit} 혜택을 통해 경제적 도움을 받으실 수 있으니 신청을 고려해보세요!"

        from datetime import datetime
        return PolicyExplanation(
            policy_id=policy.get("policy_id", "unknown"),
            explanation=fallback_text,
            generated_at=datetime.now().isoformat(),
            gpt_model="fallback_template"
        )

    def explain_all(self, matched_policies: List[Dict[str, Any]],
                   user_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        여러 정책에 대한 설명 생성

        Args:
            matched_policies (List[Dict[str, Any]]): 매칭된 정책 목록
            user_profile (Dict[str, Any]): 사용자 프로필

        Returns:
            List[Dict[str, Any]]: 설명이 추가된 정책 목록
        """
        try:
            explained_policies = []
            
            # 상위 5개만 GPT로 설명 생성 (응답 시간 최적화)
            max_gpt_explanations = 5
            
            for i, policy in enumerate(matched_policies):
                # 정책 정보 추출
                score = policy.get("score", 0.0)
                match_reasons = policy.get("match_reasons", [])

                # 상위 N개만 GPT 사용, 나머지는 Fallback
                if i < max_gpt_explanations:
                     explanation_result = self.generate_explanation(
                        policy, user_profile, score, match_reasons
                    )
                else:
                    explanation_result = self._get_fallback_explanation(policy, user_profile, score)

                # 원본 정책 정보에 설명 추가
                policy_with_explanation = policy.copy()
                policy_with_explanation["explanation"] = explanation_result.explanation
                policy_with_explanation["explanation_meta"] = {
                    "generated_at": explanation_result.generated_at,
                    "gpt_model": explanation_result.gpt_model
                }

                explained_policies.append(policy_with_explanation)

                # API 호출 간격 (Rate Limit 방지) - GPT 호출시에만 적용
                if i < max_gpt_explanations and self.is_available:
                    time.sleep(0.1)

            print(f"✅ Agent4: {len(explained_policies)}개 정책 설명 생성 완료 (GPT: {min(len(matched_policies), max_gpt_explanations)}건)")
            return explained_policies

        except Exception as e:
            print(f"⚠️ Agent4: 다중 설명 생성 중 오류 - {e}")
            # 오류 발생 시 원본 목록 반환
            return matched_policies

    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Agent4 사용 통계 반환

        Returns:
            Dict[str, Any]: 사용 통계 정보
        """
        return {
            "agent_name": self.agent_name,
            "version": self.agent_version,
            "openai_available": self.is_available,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "status": "active" if self.is_available else "fallback_mode"
        }


# 테스트 코드
if __name__ == "__main__":
    print("🤖 Agent 4 (GPT 설명 생성) 테스트 시작...")
    print("=" * 50)

    agent4 = Agent4()

    # 테스트용 사용자 프로필
    test_user_profile = {
        "age": 25,
        "region": "서울",
        "income": 3000,
        "employment": "구직자",
        "interest": "일자리"
    }

    # 테스트용 정책 데이터
    test_policy = {
        "policy_id": "JOB_001",
        "title": "청년내일채움공제",
        "category": "일자리",
        "benefit": "2년 만기시 300만원~1200만원 지급",
        "deadline": "연중 상시",
        "score": 93.5,
        "match_reasons": [
            "나이 조건 부합 (15-34세)",
            "지역 조건 부합 (전국)",
            "고용 상태 적합 (구직자)"
        ]
    }

    # Agent4 상태 확인
    print(f"📊 Agent4 상태:")
    stats = agent4.get_usage_stats()
    for key, value in stats.items():
        print(f"  - {key}: {value}")

    print("\n" + "=" * 30)
    print("📋 단일 정책 설명 생성 테스트")
    print("=" * 30)

    # 설명 생성 테스트
    explanation = agent4.generate_explanation(
        test_policy,
        test_user_profile,
        test_policy["score"],
        test_policy["match_reasons"]
    )

    print(f"정책: {test_policy['title']}")
    print(f"점수: {test_policy['score']}점")
    print(f"설명: {explanation.explanation}")
    print(f"생성 모델: {explanation.gpt_model}")
    print(f"생성 시간: {explanation.generated_at}")

    print("\n" + "=" * 30)
    print("📋 다중 정책 설명 생성 테스트")
    print("=" * 30)

    # 여러 정책 테스트
    test_policies = [
        test_policy,
        {
            "policy_id": "FIN_001",
            "title": "청년희망적금",
            "category": "금융",
            "benefit": "월 10만원 적립시 정부지원금 10만원 추가",
            "deadline": "2024년 12월 31일",
            "score": 81.0,
            "match_reasons": ["나이 조건 부합", "소득 조건 부합"]
        }
    ]

    explained_policies = agent4.explain_all(test_policies, test_user_profile)

    for i, policy in enumerate(explained_policies, 1):
        print(f"{i}. {policy['title']} ({policy['score']}점)")
        print(f"   설명: {policy.get('explanation', '설명 없음')}")
        if 'explanation_meta' in policy:
            print(f"   모델: {policy['explanation_meta']['gpt_model']}")

    print("\n✅ Agent 4 테스트 완료!")
