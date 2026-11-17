"""
Agent 1: 사용자 프로필 수집 및 검증 에이전트
청년 정책 추천 시스템의 첫 번째 에이전트로, 사용자의 기본 정보를 수집하고 검증합니다.
"""

import uuid
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field, field_validator
from enum import Enum

# MongoDB 핸들러 임포트
try:
    from database.mongo_handler import get_mongodb_handler
except ImportError:
    print("⚠️ MongoDB 핸들러를 임포트할 수 없습니다. 데이터베이스 기능이 비활성화됩니다.")
    get_mongodb_handler = None


class RegionEnum(str, Enum):
    """한국의 시도 지역 열거형"""
    SEOUL = "서울"
    BUSAN = "부산"
    DAEGU = "대구"
    INCHEON = "인천"
    GWANGJU = "광주"
    DAEJEON = "대전"
    ULSAN = "울산"
    SEJONG = "세종"
    GYEONGGI = "경기"
    GANGWON = "강원"
    CHUNGBUK = "충북"
    CHUNGNAM = "충남"
    JEONBUK = "전북"
    JEONNAM = "전남"
    GYEONGBUK = "경북"
    GYEONGNAM = "경남"
    JEJU = "제주"
    NATIONWIDE = "전국"


class EmploymentEnum(str, Enum):
    """고용 상태 열거형"""
    EMPLOYED = "재직자"
    JOB_SEEKER = "구직자"
    SELF_EMPLOYED = "자영업"
    STUDENT = "학생"
    UNEMPLOYED = "무직"


class InterestEnum(str, Enum):
    """관심 분야 열거형"""
    EMPLOYMENT = "일자리"
    HOUSING = "주거"
    FINANCE = "금융"
    STARTUP = "창업"
    WELFARE = "복지"
    EDUCATION = "교육"


class UserProfile(BaseModel):
    """
    사용자 프로필 Pydantic 모델
    청년 정책 대상자의 기본 정보를 담는 데이터 모델
    """
    age: int = Field(
        ...,
        ge=15,
        le=39,
        description="나이 (15-39세 청년 대상)"
    )
    region: RegionEnum = Field(
        ...,
        description="거주 지역 (시도 단위)"
    )
    income: int = Field(
        ...,
        ge=0,
        description="연 소득 (만원 단위, 0 이상)"
    )
    employment: EmploymentEnum = Field(
        ...,
        description="고용 상태"
    )
    interest: Optional[Union[InterestEnum, str]] = Field(
        None,
        description="관심 분야 (선택 사항)"
    )

    @field_validator('interest', mode='before')
    @classmethod
    def validate_interest(cls, v):
        """관심 분야 전처리 (빈 문자열 -> None)"""
        if v == "" or v is None:
            return None
        return v

    @field_validator('age')
    @classmethod
    def validate_age(cls, v):
        """나이 유효성 검증"""
        if not 15 <= v <= 39:
            raise ValueError('나이는 15세 이상 39세 이하여야 합니다.')
        return v

    @field_validator('income')
    @classmethod
    def validate_income(cls, v):
        """소득 유효성 검증"""
        if v < 0:
            raise ValueError('소득은 0 이상이어야 합니다.')
        return v

    @field_validator('region')
    @classmethod
    def validate_region(cls, v):
        """지역명 정규화"""
        region_mapping = {
            "서울특별시": "서울", "서울시": "서울",
            "부산광역시": "부산", "부산시": "부산",
            "대구광역시": "대구", "대구시": "대구",
            "인천광역시": "인천", "인천시": "인천",
            "광주광역시": "광주", "광주시": "광주",
            "대전광역시": "대전", "대전시": "대전",
            "울산광역시": "울산", "울산시": "울산",
            "세종특별자치시": "세종",
            "경기도": "경기",
            "강원도": "강원", "강원특별자치도": "강원",
            "충청북도": "충북",
            "충청남도": "충남",
            "전라북도": "전북", "전북특별자치도": "전북",
            "전라남도": "전남",
            "경상북도": "경북",
            "경상남도": "경남",
            "제주특별자치도": "제주", "제주도": "제주"
        }

        if v in region_mapping:
            return region_mapping[v]
        return v

    class Config:
        """Pydantic 설정"""
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "age": 25,
                "region": "서울",
                "income": 3000,
                "employment": "재직자",
                "interest": "창업"
            }
        }


class Agent1:
    """
    Agent 1: 사용자 프로필 수집 및 검증 에이전트

    주요 기능:
    - 사용자 기본 정보 수집
    - 입력 데이터 검증
    - 고유 프로필 ID 생성
    - 청년 정책 대상자 여부 확인
    """

    def __init__(self, use_database: bool = True):
        """Agent1 초기화

        Args:
            use_database (bool): MongoDB 사용 여부
        """
        self.agent_name = "Profile Collection Agent"
        self.agent_version = "1.0.0"
        self.use_database = use_database

        # MongoDB 핸들러 초기화
        self.db_handler = None
        if self.use_database and get_mongodb_handler:
            try:
                self.db_handler = get_mongodb_handler()
                if self.db_handler.is_connected:
                    print(f"✅ {self.agent_name}: MongoDB 연결 성공")
                else:
                    print(f"⚠️ {self.agent_name}: MongoDB 연결 실패, 로컬 모드로 실행")
                    self.db_handler = None
            except Exception as e:
                print(f"⚠️ {self.agent_name}: MongoDB 초기화 실패 - {e}")
                self.db_handler = None

    def collect_profile(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        사용자 프로필 수집 및 검증

        Args:
            user_input (Dict[str, Any]): 사용자 입력 데이터

        Returns:
            Dict[str, Any]: 처리 결과 (성공 여부, 프로필 ID, 오류 메시지 등)
        """
        try:
            # 1. 입력 데이터 검증
            validation_result = self.validate_only(user_input)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": validation_result["error"],
                    "profile_id": None
                }

            # 2. UserProfile 객체 생성
            profile = UserProfile(**user_input)

            # 3. 고유 프로필 ID 생성
            profile_id = self._generate_profile_id()
            access_token = secrets.token_urlsafe(32)

            # 4. MongoDB에 저장
            db_save_result = None
            if self.use_database:
                if not self.db_handler:
                     return {
                        "success": False,
                        "error": "데이터베이스 연결이 초기화되지 않았습니다.",
                        "profile_id": None
                     }
                
                try:
                    # UserProfile을 MongoDB 저장 형식으로 변환
                    profile_dict = profile.model_dump()
                    profile_dict["profile_id"] = profile_id
                    profile_dict["access_token_hash"] = hashlib.sha256(access_token.encode()).hexdigest()
                    profile_dict["access_token_expires_at"] = datetime.now(timezone.utc) + timedelta(days=30)

                    db_save_result = self.db_handler.save_user_profile(profile_dict)
                    
                    if not db_save_result.get("success"):
                        error_msg = db_save_result.get('error', 'DB 저장 실패')
                        print(f"⚠️ DB 저장 실패: {error_msg}")
                        return {
                            "success": False,
                            "error": f"프로필을 데이터베이스에 저장할 수 없습니다: {error_msg}",
                            "profile_id": None
                        }
                        
                except Exception as e:
                    print(f"⚠️ DB 저장 중 오류: {e}")
                    return {
                        "success": False,
                        "error": f"데이터베이스 저장 중 오류가 발생했습니다: {str(e)}",
                        "profile_id": None
                    }

            # 5. 성공 응답 반환
            response = {
                "success": True,
                "profile_id": profile_id,
                "access_token": access_token,
                "profile_data": profile.model_dump(),
                "message": f"프로필이 성공적으로 생성되었습니다. (ID: {profile_id})",
                "agent": self.agent_name,
                "database_saved": True
            }

            return response

        except ValueError as ve:
            return {
                "success": False,
                "error": f"입력 값 오류: {str(ve)}",
                "profile_id": None
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"프로필 처리 중 오류가 발생했습니다: {str(e)}",
                "profile_id": None
            }

    def validate_only(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        입력 데이터 검증만 수행 (프로필 생성하지 않음)

        Args:
            user_input (Dict[str, Any]): 사용자 입력 데이터

        Returns:
            Dict[str, Any]: 검증 결과
        """
        try:
            # 필수 필드 확인
            required_fields = ["age", "region", "income", "employment"]
            missing_fields = [field for field in required_fields if field not in user_input]

            if missing_fields:
                return {
                    "valid": False,
                    "error": f"필수 필드가 누락되었습니다: {', '.join(missing_fields)}"
                }

            # Pydantic 모델로 검증 시도
            profile = UserProfile(**user_input)

            # 청년 정책 대상자 여부 확인
            if not self._is_youth_policy_eligible(profile):
                return {
                    "valid": False,
                    "error": "청년 정책 대상자가 아닙니다. (15-39세 연령 범위 확인 필요)"
                }

            return {
                "valid": True,
                "message": "입력 데이터가 유효합니다.",
                "profile_summary": self._get_profile_summary(profile)
            }

        except ValueError as ve:
            return {
                "valid": False,
                "error": f"데이터 검증 실패: {str(ve)}"
            }
        except Exception as e:
            return {
                "valid": False,
                "error": f"검증 중 오류가 발생했습니다: {str(e)}"
            }

    def _generate_profile_id(self) -> str:
        """고유한 프로필 ID 생성"""
        return f"profile_{uuid.uuid4().hex}"

    def update_profile(self, profile_id: str, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """Update validated profile fields without changing its capability."""
        if not self.db_handler:
            return {"success": False, "error": "데이터베이스 연결이 없습니다."}
        validation = self.validate_only(user_input)
        if not validation["valid"]:
            return {"success": False, "error": validation["error"]}
        return self.db_handler.update_user_profile(profile_id, UserProfile(**user_input).model_dump())

    def _is_youth_policy_eligible(self, profile: UserProfile) -> bool:
        """
        청년 정책 대상자 여부 확인

        Args:
            profile (UserProfile): 사용자 프로필

        Returns:
            bool: 대상자 여부
        """
        # 기본적으로 15-39세 범위는 UserProfile의 validator에서 확인됨
        # 추가적인 정책별 조건이 있다면 여기서 확인
        return 15 <= profile.age <= 39

    def _get_profile_summary(self, profile: UserProfile) -> str:
        """
        프로필 요약 정보 생성

        Args:
            profile (UserProfile): 사용자 프로필

        Returns:
            str: 프로필 요약
        """
        interest_text = f", 관심분야: {profile.interest}" if profile.interest else ""
        return (
            f"{profile.age}세, {profile.region} 거주, "
            f"연소득 {profile.income:,}만원, {profile.employment}"
            f"{interest_text}"
        )

    def get_supported_regions(self) -> List[str]:
        """지원 가능한 지역 목록 반환"""
        return [region.value for region in RegionEnum]

    def get_supported_employments(self) -> List[str]:
        """지원 가능한 고용 상태 목록 반환"""
        return [emp.value for emp in EmploymentEnum]

    def get_supported_interests(self) -> List[str]:
        """지원 가능한 관심 분야 목록 반환"""
        return [interest.value for interest in InterestEnum]

    def get_profile_from_database(self, profile_id: str) -> Dict[str, Any]:
        """데이터베이스에서 프로필 조회

        Args:
            profile_id (str): 조회할 프로필 ID

        Returns:
            Dict[str, Any]: 조회 결과
        """
        if not self.db_handler:
            return {
                "success": False,
                "error": "데이터베이스 연결이 없습니다."
            }

        try:
            return self.db_handler.get_user_profile(profile_id)
        except Exception as e:
            return {
                "success": False,
                "error": f"프로필 조회 중 오류: {str(e)}"
            }

    def get_database_status(self) -> Dict[str, Any]:
        """데이터베이스 연결 상태 확인

        Returns:
            Dict[str, Any]: 연결 상태 정보
        """
        if not self.db_handler:
            return {
                "connected": False,
                "message": "MongoDB 핸들러가 초기화되지 않았습니다."
            }

        return self.db_handler.test_connection()


# 테스트 코드
if __name__ == "__main__":
    print("🤖 Agent 1 (프로필 수집) 테스트 시작...")
    print("=" * 50)

    agent1 = Agent1()

    # 테스트 케이스 1: 정상 케이스
    print("\n📋 테스트 1: 정상적인 프로필 데이터")
    test_data_1 = {
        "age": 28,
        "region": "서울",
        "income": 3500,
        "employment": "재직자",
        "interest": "창업"
    }
    result1 = agent1.collect_profile(test_data_1)
    print(f"결과: {result1['success']}")
    if result1['success']:
        print(f"프로필 ID: {result1['profile_id']}")
        print(f"메시지: {result1['message']}")
    else:
        print(f"오류: {result1['error']}")

    # 테스트 케이스 2: 나이 초과 케이스
    print("\n📋 테스트 2: 나이 초과 (40세)")
    test_data_2 = {
        "age": 40,
        "region": "부산",
        "income": 4000,
        "employment": "자영업"
    }
    result2 = agent1.collect_profile(test_data_2)
    print(f"결과: {result2['success']}")
    print(f"오류: {result2['error']}")

    # 테스트 케이스 3: 잘못된 지역 케이스
    print("\n📋 테스트 3: 잘못된 지역명")
    test_data_3 = {
        "age": 25,
        "region": "잘못된지역",
        "income": 2500,
        "employment": "구직자"
    }
    result3 = agent1.collect_profile(test_data_3)
    print(f"결과: {result3['success']}")
    print(f"오류: {result3['error']}")

    # 테스트 케이스 4: 검증만 수행
    print("\n📋 테스트 4: 검증만 수행")
    validation_result = agent1.validate_only(test_data_1)
    print(f"검증 결과: {validation_result['valid']}")
    if validation_result['valid']:
        print(f"프로필 요약: {validation_result['profile_summary']}")

    # 지원 가능한 옵션들 출력
    print("\n📋 지원 가능한 옵션들:")
    print(f"지역: {agent1.get_supported_regions()}")
    print(f"고용상태: {agent1.get_supported_employments()}")
    print(f"관심분야: {agent1.get_supported_interests()}")

    print("\n✅ Agent 1 테스트 완료!")
