"""
청년 정책 추천 시스템 - FastAPI 서버
Multi-Agent 협업 기반 청년 맞춤형 정책자금 추천 시스템
"""

import hmac
import os
import time
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Path, Request, Depends, Header
from starlette.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
import json
from core.profile_access import require_profile_access
from core.ai_budget import reserve_policy_calls
from typing import List, Optional, Dict, Any
from datetime import datetime

# Core modules
from core.config import get_settings
from core.logging import setup_logging, get_api_logger, log_system_info
from core.performance import setup_performance_optimizations, get_performance_stats, monitor_performance, cache_manager
from core.security import (
    SecureBaseModel, SecureProfileRequest, rate_limit, secure_endpoint,
    get_security_headers, SecurityMiddleware
)

# MongoDB 핸들러 및 Agent 임포트
from database.mongo_handler import get_mongodb_handler
from scheduler import get_scheduler

# 설정 로드
settings = get_settings()
api_logger = get_api_logger()


def require_admin_refresh_token(x_admin_token: Optional[str]) -> None:
    """수동 정책 갱신 API의 관리자 토큰 검사.

    ADMIN_REFRESH_TOKEN이 설정돼 있으면 X-Admin-Token 헤더를 상수 시간 비교로 검증한다.
    미설정 상태에서는 운영(production) 환경이면 갱신을 막고, 개발 환경이면 기존 동작을 유지한다.
    """
    expected = (os.getenv("ADMIN_REFRESH_TOKEN") or "").strip()
    if not expected:
        if settings.is_production():
            raise HTTPException(
                status_code=503,
                detail="ADMIN_REFRESH_TOKEN이 설정되지 않아 수동 갱신을 사용할 수 없습니다.",
            )
        return

    provided = (x_admin_token or "").strip()
    if not provided or not hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8")):
        raise HTTPException(
            status_code=401,
            detail="관리자 토큰이 필요합니다.",
            headers={"WWW-Authenticate": "X-Admin-Token"},
        )

# 애플리케이션 생명주기 관리
@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작 및 종료 이벤트 관리"""
    # 시작 이벤트
    setup_logging()
    log_system_info()

    # MongoDB 연결 및 성능 최적화
    global mongo_handler
    try:
        mongo_handler = get_mongodb_handler()
        if mongo_handler and mongo_handler.is_connected:
            setup_performance_optimizations(mongo_handler)
            api_logger.info("시스템 초기화 완료")
            
            # 정책 자동 갱신 스케줄러 시작
            scheduler = get_scheduler()
            scheduler.start()
    except Exception as e:
        api_logger.error(f"시스템 초기화 실패: {e}")

    yield

    # 종료 이벤트
    try:
        scheduler = get_scheduler()
        scheduler.stop()
    except:
        pass
    api_logger.info("시스템 종료")

# FastAPI 앱 생성
app = FastAPI(
    title=settings.app_name,
    description="""Multi-Agent 협업 기반 청년 맞춤형 정책자금 추천 시스템

## 🎯 주요 기능

- **🔐 보안 강화**: 입력 검증, 레이트 제한, XSS 방지
- **⚡ 성능 최적화**: 캐싱, 인덱싱, 모니터링
- **👤 프로필 관리**: 사용자 프로필 생성, 조회, 수정
- **📊 정책 조회**: 필터링 및 페이지네이션 지원
- **🎯 맞춤 추천**: AI 기반 개인화된 정책 추천
- **🔍 매칭 시스템**: 정확한 정책 매칭 알고리즘
- **🤖 설명 생성**: GPT 기반 정책 설명
- **📈 모니터링**: 실시간 성능 및 사용 통계

## 🚀 시작하기

1. 프로필 생성: `POST /api/profile`
2. 정책 조회: `GET /api/policies`
3. 통합 추천: `POST /api/orchestrator`
4. 성능 통계: `GET /api/stats`
""",
    version=settings.app_version,
    contact={
        "name": "청년 정책 추천 시스템 팀",
        "email": "contact@youth-policy.kr"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    lifespan=lifespan
)

# 보안 미들웨어 추가
app.add_middleware(SecurityMiddleware)

# CORS 미들웨어 설정
cors_config = settings.get_cors_config()
app.add_middleware(
    CORSMiddleware,
    **cors_config
)

# MongoDB 핸들러 전역 인스턴스
mongo_handler = None

# 서버 시작 시 MongoDB 초기화
@app.on_event("startup")
async def startup_event():
    """서버 시작 시 실행되는 이벤트"""
    global mongo_handler
    try:
        mongo_handler = get_mongodb_handler()
        if mongo_handler.is_connected:
            print("✅ FastAPI: MongoDB 핸들러 연결 성공")
        else:
            print("⚠️ FastAPI: MongoDB 연결 실패, 로컬 모드로 실행")
    except Exception as e:
        print(f"⚠️ FastAPI: MongoDB 초기화 실패 - {e}")

# Pydantic 모델들
class ProfileRequest(BaseModel):
    """프로필 생성 요청 모델"""
    age: int = Field(..., ge=18, le=39, description="나이 (18-39세)")
    region: str = Field(..., min_length=1, description="거주 지역")
    income: int = Field(..., ge=0, description="연소득 (만원 단위)")
    employment: str = Field(..., description="고용 상태 (구직자, 재직자, 자영업 등)")
    interest: Optional[str] = Field(None, description="관심 분야")

    class Config:
        schema_extra = {
            "example": {
                "age": 28,
                "region": "서울",
                "income": 3000,
                "employment": "재직자",
                "interest": "창업"
            }
        }

class ProfileResponse(BaseModel):
    """프로필 생성 응답 모델"""
    success: bool
    profile_id: str
    access_token: str
    message: str

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "profile_id": "profile_123456789",
                "message": "프로필이 성공적으로 생성되었습니다. (데이터베이스 저장 완료)"
            }
        }

class PolicyItem(BaseModel):
    """정책 항목 모델"""
    id: str
    title: str
    description: str
    category: str

class RecommendRequest(BaseModel):
    """추천 요청 모델"""
    profile_id: str

class RecommendResponse(BaseModel):
    """추천 응답 모델"""
    success: bool
    profile_id: str
    recommendations: List[PolicyItem]
    message: str

class MatchRequest(BaseModel):
    """정책 매칭 요청 모델"""
    age: int
    region: str
    income: int
    employment: str
    interest: Optional[str] = None
    min_score: Optional[float] = 40.0
    max_results: Optional[int] = 10

class MatchResult(BaseModel):
    """매칭 결과 개별 정책 모델"""
    policy_id: str
    title: str
    category: str
    score: float
    match_reasons: List[str]
    benefit_summary: str
    deadline: Optional[str] = None

class MatchResponse(BaseModel):
    """정책 매칭 응답 모델"""
    success: bool
    message: str
    user_profile_summary: str
    total_matches: int
    avg_score: float
    category_distribution: Optional[Dict[str, int]] = None
    recommendations: List[MatchResult]

class ExplainRequest(BaseModel):
    """정책 설명 요청 모델"""
    age: int
    region: str = Field(..., max_length=30)
    income: int
    employment: str = Field(..., max_length=30)
    interest: Optional[str] = Field(None, max_length=200)
    policies: List[Dict[str, Any]] = Field(..., min_length=1, max_length=10)

    @field_validator("policies")
    @classmethod
    def bounded_policy_text(cls, value):
        if any(len(json.dumps(policy, ensure_ascii=False)) > 6000 for policy in value):
            raise ValueError("정책 설명 입력이 너무 큽니다.")
        return value

class ExplainedPolicy(BaseModel):
    """설명이 포함된 정책 모델"""
    policy_id: str
    title: str
    category: str
    score: float
    match_reasons: List[str]
    benefit_summary: str
    deadline: Optional[str] = None
    explanation: str
    explanation_meta: Optional[Dict[str, str]] = None

class ExplainResponse(BaseModel):
    """정책 설명 응답 모델"""
    success: bool
    message: str
    user_profile_summary: str
    total_explained: int
    policies: List[ExplainedPolicy]

class OrchestratorRequest(BaseModel):
    """Orchestrator 추천 요청 모델"""
    age: int
    region: str = Field(..., max_length=30)
    income: int
    employment: str = Field(..., max_length=30)
    interest: Optional[str] = Field(None, max_length=200)
    min_score: Optional[float] = 40.0
    max_results: int = Field(10, ge=1, le=10)

class OrchestratorResponse(BaseModel):
    profile_id: Optional[str] = None
    access_token: Optional[str] = None
    """Orchestrator 추천 응답 모델"""
    session_id: str
    success: bool
    message: str
    processing_time: float
    steps_summary: List[Dict[str, Any]]
    recommendation_result: Optional[Dict[str, Any]] = None
    error_detail: Optional[str] = None
    generated_at: str


# 기본 엔드포인트
@app.get(
    "/",
    response_model=Dict[str, Any],
    tags=["시스템 정보"],
    summary="시스템 정보 조회",
    description="청년 정책 추천 시스템의 기본 정보와 사용 가능한 엔드포인트 목록을 반환합니다."
)
async def root():
    """시스템 정보 반환"""
    return {
        "service": "청년 정책 추천 시스템",
        "version": "1.0.0",
        "description": "Multi-Agent 협업 기반 청년 맞춤형 정책자금 추천 시스템",
        "status": "running",
        "database_connected": mongo_handler.is_connected if mongo_handler else False,
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "profile": "/api/profile",
            "policies": "/api/policies",
            "recommend": "/api/recommend",
            "match": "/api/match",
            "explain": "/api/explain",
            "orchestrator": "/api/orchestrator"
        }
    }

@app.get(
    "/health",
    response_model=Dict[str, Any],
    tags=["시스템 정보"],
    summary="헬스 체크",
    description="시스템과 데이터베이스의 연결 상태를 확인합니다."
)
async def health_check():
    """헬스 체크 (MongoDB 상태 포함)"""
    health_status = {
        "status": "healthy",
        "database": "disconnected",
        "timestamp": None
    }

    try:
        # MongoDB 연결 상태 확인
        if mongo_handler:
            db_status = mongo_handler.test_connection()
            if db_status.get("connected"):
                health_status["database"] = "connected"
                health_status["database_info"] = {
                    "name": db_status.get("database_name"),
                    "collections": db_status.get("collections_count"),
                    "size_mb": db_status.get("database_size_mb")
                }
            else:
                health_status["database_error"] = db_status.get("error")

        from datetime import datetime
        health_status["timestamp"] = datetime.now().isoformat()

    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["error"] = str(e)

    return health_status


# 스케줄러 관련 API
@app.get(
    "/api/scheduler/status",
    tags=["시스템 관리"],
    summary="스케줄러 상태 조회",
    description="정책 자동 갱신 스케줄러의 상태를 조회합니다."
)
async def get_scheduler_status():
    """스케줄러 상태 조회"""
    scheduler = get_scheduler()
    return scheduler.get_status()


@app.post(
    "/api/scheduler/refresh",
    tags=["시스템 관리"],
    summary="정책 수동 갱신 (관리자 전용)",
    description=(
        "온통청년 API에서 최신 정책 데이터를 수동으로 갱신합니다. "
        "ADMIN_REFRESH_TOKEN 환경변수가 설정된 경우 X-Admin-Token 헤더가 필요합니다."
    ),
    responses={
        200: {"description": "갱신 결과"},
        401: {"description": "관리자 토큰 누락 또는 불일치"},
        503: {"description": "ADMIN_REFRESH_TOKEN 미설정 (운영 환경)"}
    }
)
async def manual_refresh_policies(x_admin_token: Optional[str] = Header(default=None)):
    """정책 데이터 수동 갱신 (관리자 전용)"""
    require_admin_refresh_token(x_admin_token)
    scheduler = get_scheduler()
    result = await scheduler.refresh_policies()
    return result


# API 엔드포인트들
@app.post(
    "/api/profile",
    response_model=ProfileResponse,
    tags=["프로필 관리"],
    summary="프로필 생성",
    description="사용자의 기본 정보를 받아 프로필을 생성하고 데이터베이스에 저장합니다.",
    responses={
        200: {"description": "프로필 생성 성공"},
        400: {"description": "잘못된 요청 데이터"},
        500: {"description": "서버 오류"}
    }
)
async def create_profile(profile_data: ProfileRequest):
    """프로필 생성 (Agent1 + MongoDB 통합)"""
    try:
        # Agent1 임포트 및 초기화 (MongoDB 사용 가능한 경우 DB 연동)
        from agents.agent1_profile import Agent1

        # MongoDB 핸들러 연결 상태에 따라 DB 사용 여부 결정
        use_database = mongo_handler is not None and mongo_handler.is_connected
        agent1 = Agent1(use_database=use_database)

        # 프로필 데이터를 딕셔너리로 변환
        user_input = profile_data.dict()

        # Agent1으로 프로필 수집, 검증 및 DB 저장
        result = agent1.collect_profile(user_input)

        if result["success"]:
            # 응답 메시지에 DB 저장 상태 포함
            message = "프로필이 성공적으로 생성되었습니다."
            if result.get("database_saved"):
                message += " (데이터베이스 저장 완료)"
            elif result.get("database_error"):
                message += f" (데이터베이스 저장 실패: {result['database_error']})"

            return ProfileResponse(
                success=True,
                profile_id=result["profile_id"],
                access_token=result["access_token"],
                message=message
            )
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"프로필 생성 중 오류가 발생했습니다: {str(e)}")


@app.get(
    "/api/policy/{policy_id}",
    tags=["정책 조회"],
    summary="정책 상세 조회",
    description="특정 정책 ID를 사용하여 상세 정보를 조회합니다.",
    responses={
        200: {"description": "정책 상세 정보"},
        404: {"description": "정책을 찾을 수 없음"},
        500: {"description": "서버 오류"}
    }
)
async def get_policy_detail(policy_id: str = Path(..., description="조회할 정책 ID")):
    """정책 상세 조회"""
    try:
        from agents.agent2_data import Agent2

        use_database = mongo_handler is not None and mongo_handler.is_connected
        agent2 = Agent2(use_database=use_database)

        # 특정 정책 조회
        result = agent2.get_policy_by_id(policy_id)

        if result and result.get("success"):
            policy = result["policy"]
            return {
                "success": True,
                "policy": {
                    "id": policy.get("policy_id"),
                    "title": policy.get("title"),
                    "description": policy.get("benefit"),
                    "category": policy.get("category"),
                    "target_age": f"{policy.get('target_age_min', 18)}-{policy.get('target_age_max', 39)}세",
                    "target_region": policy.get("target_regions", ["전국"]),
                    "target_employment": policy.get("target_employment", []),
                    "budget_max": policy.get("budget_max"),
                    "deadline": policy.get("deadline"),
                    "application_url": policy.get("application_url")
                },
                "message": "정책 상세 조회 완료"
            }
        else:
            raise HTTPException(status_code=404, detail="해당 정책을 찾을 수 없습니다.")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"정책 조회 중 오류가 발생했습니다: {str(e)}")


@app.put(
    "/api/profile/{user_id}",
    tags=["프로필 관리"],
    summary="프로필 수정",
    description="사용자 ID를 사용하여 프로필 정보를 업데이트합니다.",
    responses={
        200: {"description": "프로필 수정 성공"},
        404: {"description": "프로필을 찾을 수 없음"},
        500: {"description": "서버 오류"}
    }
)
async def update_profile(
    user_id: str = Path(..., description="업데이트할 사용자 ID"),
    profile_data: ProfileRequest = ...,
    authorization: Optional[str] = Header(None),
):
    """프로필 수정"""
    try:
        require_profile_access(mongo_handler, user_id, authorization)
        if not mongo_handler or not mongo_handler.is_connected:
            raise HTTPException(
                status_code=503,
                detail="데이터베이스에 연결되지 않았습니다."
            )

        from agents.agent1_profile import Agent1
        agent1 = Agent1(use_database=True)

        # 프로필 수정
        result = agent1.update_profile(user_id, profile_data.dict())

        if result.get("success"):
            return {
                "success": True,
                "profile_id": user_id,
                "message": "프로필이 성공적으로 업데이트되었습니다."
            }
        else:
            raise HTTPException(status_code=404, detail=result.get("error", "프로필을 찾을 수 없습니다."))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"프로필 업데이트 중 오류가 발생했습니다: {str(e)}")


@app.get(
    "/api/user/{user_id}/history",
    tags=["사용자 이력"],
    summary="추천 이력 조회",
    description="사용자의 정책 추천 이력을 조회합니다.",
    responses={
        200: {"description": "추천 이력 조회 성공"},
        404: {"description": "사용자를 찾을 수 없음"},
        500: {"description": "서버 오류"}
    }
)
async def get_user_history(user_id: str = Path(..., description="조회할 사용자 ID"), authorization: Optional[str] = Header(None)):
    """추천 이력 조회"""
    try:
        require_profile_access(mongo_handler, user_id, authorization)
        if not mongo_handler or not mongo_handler.is_connected:
            raise HTTPException(
                status_code=503,
                detail="데이터베이스에 연결되지 않았습니다."
            )

        # 실제 DB에서 조회
        history_collection = mongo_handler.get_collection("recommendation_history")
        history_records = list(history_collection.find({"user_id": user_id}).sort("created_at", -1))

        if not history_records:
            return {
                "success": True,
                "user_id": user_id,
                "history": [],
                "total_sessions": 0,
                "message": "추천 이력이 없습니다."
            }

        # 이력 데이터 가공
        history = []
        for record in history_records:
            history.append({
                "date": record.get("created_at", datetime.now()).isoformat(),
                "session_id": record.get("session_id"),
                "recommended_policies": len(record.get("recommendations", [])),
                "avg_score": record.get("avg_score", 0),
                "top_category": record.get("top_category", "")
            })

        return {
            "success": True,
            "user_id": user_id,
            "history": history,
            "total_sessions": len(history),
            "message": f"{len(history)}개의 추천 이력을 찾았습니다."
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 이력 조회 중 오류가 발생했습니다: {str(e)}")

@app.get(
    "/api/policies",
    response_model=List[PolicyItem],
    tags=["정책 조회"],
    summary="정책 목록 조회",
    description="필터링 옵션과 함께 정책 목록을 조회합니다. 카테고리, 지역, 페이지네이션을 지원합니다.",
    responses={
        200: {"description": "정책 목록 조회 성공"},
        500: {"description": "서버 오류"}
    }
)
async def get_policies(
    category: Optional[str] = Query(None, description="정책 카테고리 (예: 일자리, 주거, 창업)"),
    region: Optional[str] = Query(None, description="대상 지역 (예: 서울, 경기)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    limit: int = Query(20, ge=1, le=100, description="페이지당 결과 수")
):
    """정책 목록 조회 (Agent2 + MongoDB 연동)"""
    try:
        # Agent2 임포트 및 초기화
        from agents.agent2_data import Agent2, PolicyFilter

        # MongoDB 연결 상태에 따라 DB 사용 여부 결정
        use_database = mongo_handler is not None and mongo_handler.is_connected
        agent2 = Agent2(use_database=use_database)

        # 필터 조건 설정
        filter_conditions = None
        if category:
            filter_conditions = PolicyFilter(category=category)

        # Agent2를 통해 정책 조회
        result = agent2.get_policies_from_db(filter_conditions)

        if result["success"]:
            policies = result["policies"]

            # PolicyItem 형식으로 변환
            policy_items = []
            for policy in policies:
                policy_items.append(PolicyItem(
                    id=policy.get("policy_id", ""),
                    title=policy.get("title", ""),
                    description=policy.get("benefit", policy.get("title", "")),  # benefit을 description으로 사용
                    category=policy.get("category", "")
                ))

            return policy_items
        else:
            # Agent2 실패 시 에러 반환
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "정책 목록을 조회할 수 없습니다.")
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"정책 조회 중 오류가 발생했습니다: {str(e)}")

@app.post("/api/recommend", response_model=RecommendResponse)
async def get_recommendations(request: RecommendRequest):
    """맞춤형 정책 추천 (레거시 호환)"""
    try:
        # 임시 추천 로직 - 레거시 호환용
        recommendations = [
            PolicyItem(
                id="rec_001",
                title="맞춤형 청년 창업 지원",
                description="회원님의 프로필에 맞는 창업 지원 프로그램",
                category="창업"
            ),
            PolicyItem(
                id="rec_002",
                title="청년 금융 지원 프로그램",
                description="소득 수준에 맞는 금융 지원 서비스",
                category="금융"
            )
        ]

        return RecommendResponse(
            success=True,
            profile_id=request.profile_id,
            recommendations=recommendations,
            message="맞춤형 정책 추천이 완료되었습니다. (레거시 버전)"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 처리 중 오류가 발생했습니다: {str(e)}")


@app.post("/api/orchestrator", response_model=OrchestratorResponse)
async def orchestrator_recommendation(request: OrchestratorRequest, http_request: Request):
    """전체 에이전트 통합 추천 (Orchestrator)"""
    try:
        reserve_policy_calls(request.max_results, http_request.client.host if http_request.client else "unknown")
        # Orchestrator 임포트 및 초기화
        from orchestrator import AgentOrchestrator

        # MongoDB 연결 상태에 따라 DB 사용 여부 결정
        use_database = mongo_handler is not None and mongo_handler.is_connected
        orchestrator = AgentOrchestrator(use_database=use_database)

        # 사용자 입력을 dict로 변환
        user_input = {
            "age": request.age,
            "region": request.region,
            "income": request.income,
            "employment": request.employment,
            "interest": request.interest
        }

        # 전체 추천 프로세스 실행
        result = await run_in_threadpool(orchestrator.process_recommendation,
            user_input,
            min_score=request.min_score,
            max_results=request.max_results
        )

        return OrchestratorResponse(
            profile_id=result.get("profile_id"),
            access_token=result.get("access_token"),
            session_id=result["session_id"],
            success=result["success"],
            message=result["message"],
            processing_time=result["processing_time"],
            steps_summary=result["steps_summary"],
            recommendation_result=result["recommendation_result"],
            error_detail=result.get("error_detail"),
            generated_at=result["generated_at"]
        )

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="통합 추천 처리 중 오류가 발생했습니다.")


@app.post("/api/match", response_model=MatchResponse)
async def match_policies(request: MatchRequest):
    """정책 매칭 (Agent2 + Agent3 협업)"""
    try:
        # Agent2로 정책 데이터 조회
        from agents.agent2_data import Agent2
        from agents.agent3_matching import Agent3

        # MongoDB 연결 상태에 따라 DB 사용 여부 결정
        use_database = mongo_handler is not None and mongo_handler.is_connected
        agent2 = Agent2(use_database=use_database)
        agent3 = Agent3()

        # 사용자 프로필 구성
        user_profile = {
            "age": request.age,
            "region": request.region,
            "income": request.income,
            "employment": request.employment,
            "interest": request.interest
        }

        # Agent2로 정책 데이터 조회
        policies_result = agent2.get_policies_from_db()

        if not policies_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=policies_result.get("error", "정책 데이터를 조회할 수 없습니다.")
            )
        
        # DB에서 조회된 정책을 Agent3용 형식으로 변환
        policies_data = []
        for policy in policies_result.get("policies", []):
            # Agent2의 PolicySummary를 Agent3용 정책 데이터로 변환하되 실제 조건 정보 활용
            policy_data = {
                "policy_id": policy.get("policy_id"),
                "title": policy.get("title"),
                "category": policy.get("category"),
                # 실제 정책 조건 정보 사용 (없으면 기본값)
                "target_age_min": policy.get("target_age_min", 18),
                "target_age_max": policy.get("target_age_max", 39),
                "target_regions": policy.get("target_regions", ["전국"]),
                "target_employment": policy.get("target_employment", ["구직자", "재직자", "학생", "자영업"]),
                "target_income_max": policy.get("target_income_max"),
                "benefit": policy.get("benefit", ""),
                "budget_max": policy.get("budget_max"),
                "deadline": policy.get("deadline"),
                "application_url": policy.get("application_url", ""),
                # 추가 조건들도 포함
                "requirements": policy.get("requirements", []),
                "website_url": policy.get("website_url", "")
            }
            policies_data.append(policy_data)

        # Agent3로 매칭 수행
        matching_results = agent3.match_policies(
            user_profile,
            policies_data,
            min_score=request.min_score,
            max_results=request.max_results
        )

        # 매칭 요약 정보 생성
        summary = agent3.get_matching_summary(user_profile, matching_results)

        # MatchResult 형식으로 변환
        match_results = []
        for result in matching_results:
            match_results.append(MatchResult(
                policy_id=result.policy_id,
                title=result.title,
                category=result.category,
                score=result.score,
                match_reasons=result.match_reasons,
                benefit_summary=result.benefit_summary,
                deadline=result.deadline
            ))

        return MatchResponse(
            success=summary.get("success", True),
            message=summary.get("message", "매칭이 완료되었습니다."),
            user_profile_summary=summary.get("user_profile_summary", ""),
            total_matches=summary.get("total_matches", len(match_results)),
            avg_score=summary.get("avg_score", 0.0),
            category_distribution=summary.get("category_distribution"),
            recommendations=match_results
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"정책 매칭 중 오류가 발생했습니다: {str(e)}")


@app.post("/api/explain", response_model=ExplainResponse)
async def explain_policies(request: ExplainRequest, http_request: Request):
    """정책 설명 생성 (Agent4 + GPT-4 연동)"""
    try:
        # Use trusted policy data, never caller-provided prompt text.
        if not mongo_handler or not mongo_handler.is_connected:
            raise HTTPException(status_code=503, detail="정책 데이터베이스에 연결되지 않았습니다.")
        policies = []
        for item in request.policies:
            policy_id = item.get("policy_id")
            if not isinstance(policy_id, str) or not 1 <= len(policy_id) <= 100:
                raise HTTPException(status_code=422, detail="유효한 정책 ID가 필요합니다.")
            record = mongo_handler.get_collection("policies").find_one({"policy_id": policy_id})
            if not record:
                raise HTTPException(status_code=404, detail="정책을 찾을 수 없습니다.")
            policy = {key: str(record.get(key) or "")[:2000]
                      for key in ("policy_id", "title", "category", "benefit", "benefit_summary", "deadline")}
            policies.append(policy)
        reserve_policy_calls(len(policies), http_request.client.host if http_request.client else "unknown")
        # Agent4 임포트 및 초기화
        from agents.agent4_gpt import Agent4

        agent4 = Agent4()

        # 사용자 프로필 구성
        user_profile = {
            "age": request.age,
            "region": request.region,
            "income": request.income,
            "employment": request.employment,
            "interest": request.interest
        }

        # Agent4로 설명 생성
        explained_policies = await run_in_threadpool(agent4.explain_all, policies, user_profile)

        # ExplainedPolicy 형식으로 변환
        explained_results = []
        for policy in explained_policies:
            explained_results.append(ExplainedPolicy(
                policy_id=policy.get("policy_id", ""),
                title=policy.get("title", ""),
                category=policy.get("category", ""),
                score=policy.get("score", 0.0),
                match_reasons=policy.get("match_reasons", []),
                benefit_summary=policy.get("benefit_summary", ""),
                deadline=policy.get("deadline"),
                explanation=policy.get("explanation", "설명을 생성할 수 없습니다."),
                explanation_meta=policy.get("explanation_meta")
            ))

        # 사용자 프로필 요약
        profile_summary = f"{request.age}세, {request.region} 거주, 연소득 {request.income:,}만원, {request.employment}"
        if request.interest:
            profile_summary += f", 관심분야: {request.interest}"

        return ExplainResponse(
            success=True,
            message=f"{len(explained_results)}개 정책에 대한 설명이 생성되었습니다.",
            user_profile_summary=profile_summary,
            total_explained=len(explained_results),
            policies=explained_results
        )

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="정책 설명 생성 중 오류가 발생했습니다.")


# 새로운 API 엔드포인트: 프로필 조회
@app.get("/api/profile/{profile_id}")
async def get_profile(profile_id: str, authorization: Optional[str] = Header(None)):
    """프로필 조회 (MongoDB에서)"""
    try:
        require_profile_access(mongo_handler, profile_id, authorization)
        if not mongo_handler or not mongo_handler.is_connected:
            raise HTTPException(
                status_code=503,
                detail="데이터베이스에 연결되지 않았습니다."
            )

        # Agent1을 사용해서 프로필 조회
        from agents.agent1_profile import Agent1
        agent1 = Agent1(use_database=True)

        result = agent1.get_profile_from_database(profile_id)

        if result.get("success"):
            public_fields = {"profile_id", "age", "region", "income", "employment", "interest", "created_at", "updated_at"}
            result["profile"] = {key: value for key, value in result["profile"].items() if key in public_fields}
            return {
                "success": True,
                "profile": result["profile"],
                "message": "프로필 조회 완료"
            }
        else:
            raise HTTPException(status_code=404, detail=result["error"])

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"프로필 조회 중 오류가 발생했습니다: {str(e)}")


# 서버 실행 코드
if __name__ == "__main__":
    print("🚀 청년 정책 추천 시스템 서버 시작...")
    print("📍 Swagger UI: http://localhost:8000/docs")
    print("📍 ReDoc: http://localhost:8000/redoc")
    print("📍 MongoDB 연동: Stage 3 구현 완료")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
