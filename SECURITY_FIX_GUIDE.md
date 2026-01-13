# 🔒 보안 수정 가이드 - 배포 전 필수 조치

**⚠️ 긴급**: MongoDB 자격증명 노출 문제 해결

---

## 🚨 발견된 보안 이슈

### 문제점:
`backend/.env` 파일에 실제 MongoDB 자격증명이 노출되어 있음

```env
# 현재 문제 상황
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?appName=Callijisu
DATABASE_NAME=youth_policy
OPENAI_API_KEY=
```

### 위험도: 🔴 높음
- MongoDB 데이터베이스에 무단 접근 가능
- 사용자 개인정보 노출 위험
- 서비스 중단 가능성

---

## 🛠️ 즉시 수정 방법

### 1단계: 자격증명 변경
```bash
# MongoDB Atlas 접속하여 비밀번호 변경
# 1. https://cloud.mongodb.com/ 로그인
# 2. Database Access > Users 에서 callijisu 사용자 비밀번호 변경
# 3. 새로운 강력한 비밀번호 설정
```

### 2단계: .env 파일 수정
```bash
# backend/.env 파일 백업 및 수정
cd backend
cp .env .env.backup
nano .env  # 또는 다른 텍스트 에디터 사용
```

**새로운 .env 파일 내용**:
```env
# MongoDB Configuration (새 비밀번호로 수정)
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?appName=Callijisu
DATABASE_NAME=youth_policy

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Server Configuration
DEBUG=False
LOG_LEVEL=WARNING
ENVIRONMENT=production
```

### 3단계: Git에서 민감 정보 제거
```bash
# 현재 브랜치에서 .env 파일을 완전히 추적 중지
git rm --cached backend/.env
git commit -m "보안: .env 파일 추적 중지"

# .gitignore가 제대로 설정되어 있는지 확인
echo "backend/.env" >> .gitignore
git add .gitignore
git commit -m "보안: .env 파일 gitignore 추가"
```

### 4단계: 히스토리에서 민감 정보 제거 (옵션)
```bash
# 주의: 이 명령은 Git 히스토리를 변경합니다
git filter-branch --force --index-filter \
'git rm --cached --ignore-unmatch backend/.env' \
--prune-empty --tag-name-filter cat -- --all

# 원격 저장소에 강제 푸시 (주의!)
git push origin --force --all
```

---

## ✅ 보안 강화 추가 조치

### 1. 환경변수 분리
```bash
# 프로덕션 환경에서는 환경변수로 관리
export MONGODB_URI="mongodb+srv://<user>:<password>@<cluster>.mongodb.net/"
export OPENAI_API_KEY="sk-your-api-key"
export SECRET_KEY="your-secret-key"
```

### 2. IP 허용 목록 설정
```bash
# MongoDB Atlas에서:
# 1. Network Access 메뉴
# 2. IP 허용 목록에 서버 IP만 추가
# 3. 0.0.0.0/0 (모든 IP 허용) 제거
```

### 3. 데이터베이스 사용자 권한 제한
```bash
# MongoDB Atlas에서:
# 1. Database Access 메뉴
# 2. 사용자 권한을 readWrite로 제한
# 3. admin 권한 제거
```

### 4. .env.example 업데이트
```env
# backend/.env.example 파일 내용
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/database
DATABASE_NAME=youth_policy
OPENAI_API_KEY=sk-your-openai-api-key
DEBUG=True
LOG_LEVEL=INFO
ENVIRONMENT=development
SECRET_KEY=your-secret-key-here
```

---

## 🔍 수정 후 검증

### 1. 연결 테스트
```bash
cd backend
python -c "
from core.config import get_settings
settings = get_settings()
print('MongoDB URI 설정됨:', bool(settings.mongodb_uri))
print('디버그 모드:', settings.debug)
"
```

### 2. 서버 시작 테스트
```bash
uvicorn main:app --port 8000 --reload
# http://localhost:8000/health 접속하여 DB 연결 확인
```

### 3. 보안 스캔 실행
```bash
# 민감 정보 스캔
grep -r "password\|secret\|key" . --exclude-dir=venv --exclude-dir=.git

# .env 파일이 Git에서 제외되었는지 확인
git status | grep .env || echo "✅ .env 파일이 추적되지 않음"
```

---

## 📋 배포 전 최종 체크리스트

### 보안 체크:
- [ ] MongoDB 비밀번호 변경 완료
- [ ] .env 파일에서 실제 자격증명 제거
- [ ] .gitignore에 .env 파일 추가 확인
- [ ] Git 히스토리에서 민감 정보 제거 (필요시)
- [ ] MongoDB IP 허용 목록 설정
- [ ] 데이터베이스 사용자 권한 최소화

### 환경 설정 체크:
- [ ] DEBUG=False로 설정
- [ ] LOG_LEVEL=WARNING으로 설정
- [ ] SECRET_KEY 강력한 값으로 설정
- [ ] OpenAI API 키 설정 (선택사항)

### 테스트 체크:
- [ ] MongoDB 연결 테스트 통과
- [ ] 서버 시작 정상
- [ ] 핵심 API 엔드포인트 테스트 통과

---

## 🚀 배포 명령어

### 로컬 테스트:
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 프로덕션 배포:
```bash
# 환경변수 설정
export MONGODB_URI="your_secure_mongodb_uri"
export OPENAI_API_KEY="your_openai_api_key"
export SECRET_KEY="your_secret_key"
export DEBUG=False

# 서버 시작 (프로덕션용)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## ⚡ 응급 연락처

**보안 문제 발견 시**:
1. 즉시 서비스 중단
2. MongoDB 비밀번호 변경
3. 의심스러운 활동 로그 확인
4. 시스템 관리자에게 연락

**문의**:
- 이메일: contact@youth-policy.kr
- GitHub Issues: [이슈 제보](https://github.com/Callijisu/youth-policy-recommender/issues)

---

**⚠️ 중요**: 이 문서의 모든 보안 조치를 완료한 후에만 시스템을 배포하시기 바랍니다.