# 🔒 보안 수정 가이드 - 청년 정책 추천 시스템

**⚠️ 긴급 보안 이슈 해결 가이드**

---

## 🚨 발견된 보안 문제

### **Critical 보안 이슈**
현재 `backend/.env` 파일에 **실제 MongoDB 자격증명이 노출**되어 있습니다.

```env
# ⚠️ 현재 위험한 상태
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?appName=Callijisu
```

### **위험도 평가**
- **위험 수준**: 🔴 **Critical (최고 위험)**
- **영향 범위**: 전체 데이터베이스 접근 권한
- **노출 범위**: GitHub 저장소, 로컬 개발 환경
- **즉시 조치 필요**: MongoDB 데이터베이스에 무단 접근 가능

---

## 🛠️ 즉시 수정 단계 (15분 내 완료)

### **1단계: MongoDB 자격증명 변경 (5분)**

```bash
# 1. MongoDB Atlas 대시보드 접속
open https://cloud.mongodb.com/

# 2. Database Access > Users로 이동
# 3. 'callijisu' 사용자의 비밀번호 변경
#    - Edit User 클릭
#    - Password 변경 (강력한 새 비밀번호)
#    - Update User 저장
```

**새 비밀번호 요구사항**:
- 최소 12자리 이상
- 대소문자, 숫자, 특수문자 포함
- 예: `SecurePass123!@#`

### **2단계: .env 파일 보안 처리 (5분)**

```bash
# 1. 현재 .env 파일 백업
cd backend
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# 2. .env 파일 수정
nano .env

# 3. 다음과 같이 수정:
```

**수정된 .env 파일 예시**:
```env
# MongoDB Configuration
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?appName=Callijisu
DATABASE_NAME=youth_policy

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Security
SECRET_KEY=super-secure-random-key-for-production

# Environment
DEBUG=False
LOG_LEVEL=WARNING
ENVIRONMENT=production
```

### **3단계: Git 보안 처리 (5분)**

```bash
# 1. .env 파일을 Git 추적에서 제거
git rm --cached backend/.env

# 2. .gitignore 확인 및 추가
echo "backend/.env" >> .gitignore

# 3. 변경사항 커밋
git add .gitignore
git commit -m "보안: .env 파일 추적 중지"

# 4. 원격 저장소 업데이트
git push origin main
```

---

## 🔧 고급 보안 조치 (권장)

### **MongoDB 보안 강화**

1. **IP 허용 목록 설정**
   ```bash
   # MongoDB Atlas에서:
   # Network Access > IP Access List
   # 1. 0.0.0.0/0 제거 (전체 허용)
   # 2. 서버 IP만 추가
   # 3. 개발자 IP만 추가
   ```

2. **데이터베이스 사용자 권한 제한**
   ```bash
   # Database Access > Database Users
   # 1. 사용자 권한을 readWrite로 제한
   # 2. admin 권한 제거
   # 3. 특정 데이터베이스로 제한
   ```

3. **연결 문자열 최적화**
   ```env
   # SSL 및 보안 옵션 추가
   MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/database?retryWrites=true&w=majority&ssl=true
   ```

### **애플리케이션 보안 강화**

1. **환경변수 분리**
   ```bash
   # 프로덕션 환경에서는 시스템 환경변수 사용
   export MONGODB_URI="mongodb+srv://..."
   export OPENAI_API_KEY="sk-..."
   export SECRET_KEY="secure-key"

   # .env 파일 삭제
   rm backend/.env
   ```

2. **비밀번호 해싱**
   ```python
   # core/security.py에 추가
   import hashlib
   import secrets

   def hash_password(password: str) -> str:
       salt = secrets.token_hex(16)
       pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
       return f"{salt}:{pwd_hash.hex()}"
   ```

3. **API 키 암호화**
   ```python
   # core/security.py에 추가
   from cryptography.fernet import Fernet

   def encrypt_api_key(key: str) -> str:
       f = Fernet(Fernet.generate_key())
       encrypted_key = f.encrypt(key.encode())
       return encrypted_key
   ```

---

## 🔍 보안 검증 및 테스트

### **1. 자격증명 유출 검사**

```bash
# Git 히스토리에서 민감 정보 검색
git log -p | grep -i "password\|secret\|key\|token"

# 현재 파일에서 민감 정보 검색
grep -r "password\|secret\|key\|token" . --exclude-dir=venv --exclude-dir=.git

# .env 파일이 Git에서 제외되었는지 확인
git status | grep .env || echo "✅ .env 파일이 추적되지 않음"
```

### **2. 연결 보안 테스트**

```bash
# MongoDB 연결 테스트 (새 자격증명)
python -c "
from core.config import get_settings
from database.mongo_handler import get_mongodb_handler

settings = get_settings()
print('MongoDB URI 설정됨:', bool(settings.mongodb_uri))

try:
    handler = get_mongodb_handler()
    status = handler.test_connection()
    print('연결 상태:', status.get('connected', False))
except Exception as e:
    print('연결 오류:', str(e))
"
```

### **3. API 보안 테스트**

```bash
# HTTPS 리디렉션 테스트 (프로덕션)
curl -I http://your-domain.com/health

# CORS 설정 테스트
curl -H "Origin: https://malicious-site.com" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: X-Requested-With" \
     -X OPTIONS \
     http://localhost:8000/api/profile

# SQL Injection 방어 테스트
curl -X POST http://localhost:8000/api/profile \
  -H "Content-Type: application/json" \
  -d '{"age":"28; DROP TABLE users;","region":"서울","income":3000,"employment":"재직자"}'
```

---

## 📋 보안 체크리스트

### **즉시 조치 완료 확인**
- [ ] MongoDB 비밀번호 변경됨
- [ ] .env 파일에서 실제 자격증명 제거됨
- [ ] .env 파일이 Git에서 제외됨
- [ ] 새로운 자격증명으로 연결 테스트 성공

### **추가 보안 조치**
- [ ] MongoDB IP 허용 목록 설정
- [ ] 데이터베이스 사용자 권한 최소화
- [ ] SSL/TLS 연결 강제
- [ ] API Rate Limiting 설정
- [ ] 로그 모니터링 시스템 구축

### **장기 보안 계획**
- [ ] 정기적인 비밀번호 변경 (월 1회)
- [ ] 보안 취약점 스캔 (주 1회)
- [ ] 접근 로그 모니터링 (일일)
- [ ] 백업 데이터 암호화
- [ ] 재해 복구 계획 수립

---

## 🚨 보안 사고 대응 절차

### **1. 즉시 대응 (5분 내)**
```bash
# 1. 서비스 중단
pkill -f uvicorn

# 2. MongoDB 사용자 비활성화
# MongoDB Atlas > Database Access > Users > Disable

# 3. API 키 무효화
# OpenAI 대시보드에서 API 키 삭제/재생성
```

### **2. 피해 조사 (30분 내)**
```bash
# 1. 접속 로그 확인
grep "suspicious_ip" /var/log/nginx/access.log

# 2. 데이터베이스 접속 로그 확인
# MongoDB Atlas > Monitoring > Access Logs

# 3. 시스템 침해 여부 확인
ps aux | grep -E "nc|netcat|wget|curl"
```

### **3. 복구 작업 (1시간 내)**
```bash
# 1. 새로운 보안 자격증명 생성
# 2. 모든 API 키 재발급
# 3. 시스템 보안 패치 적용
# 4. 서비스 재시작
# 5. 모니터링 강화
```

---

## 📊 보안 모니터링

### **실시간 모니터링**

```bash
# 1. 로그 모니터링 스크립트
#!/bin/bash
# monitor_security.sh

tail -f /var/log/application.log | while read line; do
    if echo "$line" | grep -E "FAILED_LOGIN|UNAUTHORIZED|ERROR"; then
        echo "🚨 보안 경고: $line" | mail -s "보안 알림" admin@your-domain.com
    fi
done

# 2. 네트워크 모니터링
netstat -tuln | grep :8000

# 3. 프로세스 모니터링
ps aux | grep uvicorn
```

### **주기적 보안 점검**

```bash
# 1. 일일 보안 점검 (crontab)
# 0 2 * * * /home/user/scripts/daily_security_check.sh

# 2. 주간 취약점 스캔
# 0 0 * * 0 nmap -sS -O localhost

# 3. 월간 보안 감사
# 0 0 1 * * /home/user/scripts/monthly_security_audit.sh
```

---

## 🔐 추가 보안 도구

### **1. 암호화 도구**

```python
# utils/encryption.py
from cryptography.fernet import Fernet
import os

class SecureConfig:
    def __init__(self):
        self.key = os.environ.get('ENCRYPTION_KEY', Fernet.generate_key())
        self.cipher = Fernet(self.key)

    def encrypt(self, data: str) -> str:
        return self.cipher.encrypt(data.encode()).decode()

    def decrypt(self, encrypted_data: str) -> str:
        return self.cipher.decrypt(encrypted_data.encode()).decode()
```

### **2. 로그 보안**

```python
# core/secure_logging.py
import logging
import re

class SecureFormatter(logging.Formatter):
    def format(self, record):
        # 민감 정보 마스킹
        message = super().format(record)
        message = re.sub(r'password[\'\"]*\s*[:=]\s*[\'\"]*([^\'\"]*)[\'\"]*',
                        r'password: ***', message)
        message = re.sub(r'api[_-]?key[\'\"]*\s*[:=]\s*[\'\"]*([^\'\"]*)[\'\"]*',
                        r'api_key: ***', message)
        return message
```

### **3. 입력 검증 강화**

```python
# core/validation.py
import re
from typing import Any

class SecurityValidator:
    @staticmethod
    def validate_input(data: Any) -> bool:
        """SQL Injection, XSS 방어"""
        if isinstance(data, str):
            dangerous_patterns = [
                r'<script.*?>.*?</script>',  # XSS
                r'(union|select|insert|delete|drop|update)',  # SQL Injection
                r'javascript:',  # XSS
                r'on\w+\s*=',  # Event handler XSS
            ]
            for pattern in dangerous_patterns:
                if re.search(pattern, data, re.IGNORECASE):
                    return False
        return True
```

---

## ✅ 보안 수정 완료 검증

### **최종 확인 명령어**

```bash
# 1. 자격증명 보안 확인
echo "MongoDB URI에 실제 비밀번호가 없는지 확인:"
grep -E "password|pwd" backend/.env | grep -v "your_password" || echo "✅ 안전"

# 2. Git 보안 확인
echo ".env 파일이 Git에서 제외되었는지 확인:"
git status | grep ".env" || echo "✅ 안전"

# 3. 연결 테스트
echo "새로운 자격증명으로 연결 테스트:"
python -c "
from database.mongo_handler import get_mongodb_handler
try:
    handler = get_mongodb_handler()
    status = handler.test_connection()
    print('✅ 연결 성공' if status.get('connected') else '❌ 연결 실패')
except:
    print('❌ 연결 실패 - 자격증명 확인 필요')
"

# 4. API 보안 테스트
echo "API 보안 테스트:"
curl -s http://localhost:8000/health | grep -q "healthy" && echo "✅ API 정상" || echo "❌ API 오류"
```

**모든 확인 항목이 ✅로 표시되면 보안 수정이 완료됨**

---

## 📞 긴급 연락처

### **보안 사고 발생 시**
- **즉시 연락**: 시스템 관리자 (contact@youth-policy.kr)
- **MongoDB Atlas 지원**: https://support.mongodb.com/
- **OpenAI 지원**: https://help.openai.com/

### **참고 자료**
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [MongoDB 보안 가이드](https://docs.mongodb.com/manual/security/)
- [FastAPI 보안 문서](https://fastapi.tiangolo.com/tutorial/security/)

---

**⚠️ 중요**: 이 문서의 모든 보안 조치를 완료한 후에만 시스템을 배포하십시오.

**보안 수정 완료 확인일**: 2026년 1월 9일
**담당자**: 시스템 보안팀
**문서 버전**: 1.0.0