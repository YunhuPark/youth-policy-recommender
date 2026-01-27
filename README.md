# 청년 정책 추천 시스템 🏛️

Multi-Agent 협업 기반 청년 맞춤형 정책자금 추천 시스템

## 📋 프로젝트 소개

이 시스템은 청년층이 자신에게 맞는 정부 정책과 지원 프로그램을 쉽게 찾을 수 있도록 도와주는 AI 기반 추천 플랫폼입니다. 5개의 전문 Agent가 협업하여 개인화된 정책 추천을 제공합니다.

## ✨ 주요 기능

### 🎯 개인화된 정책 추천
- 나이, 지역, 소득, 고용상태 기반 맞춤 추천
- AI 기반 정확한 매칭 알고리즘
- 실시간 정책 데이터 연동

### 📊 스마트 분석
- 정책 적합도 점수 제공 (0-100점)
- 카테고리별 추천 분포 분석
- 추천 이력 관리 및 추적

### 🤖 GPT-4 기반 설명
- 개인 맞춤형 정책 설명 생성
- 쉬운 언어로 정책 내용 해석
- 신청 방법 및 절차 안내

### 🔍 고급 검색 및 필터링
- 카테고리별 정책 검색 (창업, 주거, 일자리, 금융 등)
- 지역별 필터링
- 페이지네이션 지원

## 🛠 기술 스택

### Backend
- **FastAPI** - 고성능 웹 프레임워크
- **Python 3.12** - 메인 언어
- **MongoDB** - NoSQL 데이터베이스
- **PyMongo** - MongoDB 드라이버

### AI/ML
- **OpenAI GPT-4** - 자연어 처리 및 설명 생성
- **Multi-Agent 아키텍처** - 협업 기반 추천 시스템

### 개발 도구
- **Uvicorn** - ASGI 서버
- **Pydantic** - 데이터 검증
- **python-dotenv** - 환경 변수 관리

## 📁 프로젝트 구조

```
youth-policy-recommender/
├── backend/
│   ├── agents/                 # AI Agent 모듈들
│   │   ├── agent1_profile.py   # 프로필 수집 및 검증
│   │   ├── agent2_data.py      # 정책 데이터 관리
│   │   ├── agent3_matching.py  # 정책 매칭 알고리즘
│   │   ├── agent4_gpt.py       # GPT-4 설명 생성
│   │   └── agent5_presentation.py # 결과 정리
│   ├── database/               # 데이터베이스 관련
│   │   ├── models.py           # 데이터 모델
│   │   └── mongo_handler.py    # MongoDB 핸들러
│   ├── docs/                   # API 문서
│   ├── main.py                 # FastAPI 애플리케이션
│   ├── orchestrator.py         # Agent 통합 관리자
│   ├── requirements.txt        # 의존성 패키지
│   └── .env                    # 환경 설정
├── data/                       # 정책 데이터
├── scripts/                    # 유틸리티 스크립트
└── README.md                   # 프로젝트 문서
```

## 🚀 설치 및 실행

### 1. 저장소 클론
```bash
git clone https://github.com/Callijisu/youth-policy-recommender.git
cd youth-policy-recommender
```

### 2. 가상환경 생성 및 활성화
```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. 패키지 설치
```bash
pip install -r requirements.txt
```

### 4. 환경 변수 설정
```bash
cp .env.example .env
```

`.env` 파일을 편집하여 다음 값들을 설정하세요:
```env
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/
DATABASE_NAME=youth_policy
OPENAI_API_KEY=your_openai_api_key
DEBUG=True
LOG_LEVEL=INFO
```

### 5. MongoDB 데이터베이스 준비
- MongoDB Atlas 클러스터 생성 또는 로컬 MongoDB 설치
- 정책 데이터 초기화 (선택사항)

### 6. 서버 실행
```bash
uvicorn main:app --reload
```

서버가 성공적으로 시작되면:
- 🌐 **API 서버**: http://localhost:8000
- 📚 **API 문서**: http://localhost:8000/docs
- 📖 **ReDoc**: http://localhost:8000/redoc

## 🔧 API 사용법

### 기본 엔드포인트

#### 1. 시스템 정보 조회
```bash
curl http://localhost:8000/
```

#### 2. 헬스 체크
```bash
curl http://localhost:8000/health
```

### 프로필 관리

#### 3. 프로필 생성
```bash
curl -X POST "http://localhost:8000/api/profile" \
  -H "Content-Type: application/json" \
  -d '{
    "age": 28,
    "region": "서울",
    "income": 3000,
    "employment": "재직자",
    "interest": "창업"
  }'
```

#### 4. 프로필 조회
```bash
curl http://localhost:8000/api/profile/{profile_id}
```

#### 5. 프로필 수정
```bash
curl -X PUT "http://localhost:8000/api/profile/{user_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "age": 29,
    "region": "서울",
    "income": 3500,
    "employment": "재직자",
    "interest": "부동산"
  }'
```

### 정책 조회

#### 6. 전체 정책 목록
```bash
curl "http://localhost:8000/api/policies?page=1&limit=20"
```

#### 7. 카테고리별 정책 필터링
```bash
curl "http://localhost:8000/api/policies?category=창업&region=서울&page=1&limit=10"
```

#### 8. 정책 상세 조회
```bash
curl http://localhost:8000/api/policy/{policy_id}
```

### 추천 시스템

#### 9. 통합 정책 추천 (권장)
```bash
curl -X POST "http://localhost:8000/api/orchestrator" \
  -H "Content-Type: application/json" \
  -d '{
    "age": 28,
    "region": "서울",
    "income": 3000,
    "employment": "재직자",
    "interest": "창업",
    "min_score": 40.0,
    "max_results": 5
  }'
```

#### 10. 정책 매칭
```bash
curl -X POST "http://localhost:8000/api/match" \
  -H "Content-Type: application/json" \
  -d '{
    "age": 28,
    "region": "서울",
    "income": 3000,
    "employment": "재직자",
    "min_score": 40.0,
    "max_results": 10
  }'
```

### 사용자 이력

#### 11. 추천 이력 조회
```bash
curl http://localhost:8000/api/user/{user_id}/history
```

## 🏗️ 시스템 아키텍처

### Multi-Agent 협업 구조

```
📊 사용자 입력
    ↓
👤 Agent 1 (Profile)
    ↓ 프로필 검증 & 저장
📚 Agent 2 (Data)
    ↓ 정책 데이터 조회
🎯 Agent 3 (Matching)
    ↓ 매칭 알고리즘 실행
🤖 Agent 4 (GPT)
    ↓ 설명 생성
📋 Agent 5 (Presentation)
    ↓ 결과 정리
✨ 최종 추천 결과
```

### 데이터베이스 스키마

#### Profiles Collection
```javascript
{
  "_id": ObjectId,
  "profile_id": "string",
  "age": "number",
  "region": "string",
  "income": "number",
  "employment": "string",
  "interest": "string",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

#### Policies Collection
```javascript
{
  "_id": ObjectId,
  "policy_id": "string",
  "title": "string",
  "category": "string",
  "target_age_min": "number",
  "target_age_max": "number",
  "target_regions": ["string"],
  "target_employment": ["string"],
  "benefit": "string",
  "budget_max": "number",
  "deadline": "string",
  "application_url": "string"
}
```

## 🎯 핵심 특징

### 🔄 실시간 처리
- 비동기 처리로 빠른 응답 시간
- 대용량 정책 데이터 효율적 처리

### 🛡️ 안정성
- 포괄적인 에러 핸들링
- 표준화된 HTTP 응답 코드
- 입력 데이터 검증

### 📈 확장성
- 모듈식 Agent 아키텍처
- 새로운 정책 카테고리 쉽게 추가
- 수평적 확장 가능

### 🔒 보안
- 환경 변수를 통한 민감 정보 관리
- CORS 설정으로 안전한 API 접근

## 👥 팀원

- **개발자**: 명지수
- **이메일**: callijisu@gmail.com
- **깃허브**: https://github.com/Callijisu

## 📜 라이선스

MIT License - 자유롭게 사용, 수정, 배포 가능합니다.

## 🤝 기여하기

1. 이 저장소를 포크하세요
2. 새 기능 브랜치를 생성하세요 (`git checkout -b feature/new-feature`)
3. 변경사항을 커밋하세요 (`git commit -m 'Add new feature'`)
4. 브랜치에 푸시하세요 (`git push origin feature/new-feature`)
5. Pull Request를 생성하세요

## 📞 지원 및 문의

- **이슈 제보**: [GitHub Issues](https://github.com/Callijisu/youth-policy-recommender/issues)
- **이메일**: callijisu@gmail.com
- **문서**: [API 문서](./docs/API.md)

---

**청년을 위한, 청년에 의한 정책 추천 시스템** 🌟
