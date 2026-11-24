# GitHub Actions 워크플로 백업

원래 저장소의 `.github/workflows/` 아래에 있던 워크플로 두 개를 백업해 둔 것입니다.

- `backend-tests.yml` — 백엔드 테스트(`pytest tests -q`)
- `gitleaks.yml` — gitleaks 시크릿 스캔

이 저장소에는 GitHub 앱 권한상 `.github/workflows/` 파일을 직접 push할 수 없습니다.
아래처럼 GitHub 웹에서 옮겨 주세요.

## 옮기는 방법

1. GitHub에서 `docs/workflows/backend-tests.yml` 파일을 엽니다.
2. 오른쪽 위 **Raw** 버튼을 누르고 내용을 전체 복사합니다.
3. 저장소 상단 **Add file → Create new file**에서 파일 이름을 `.github/workflows/backend-tests.yml`로 입력합니다.
4. 복사한 내용을 붙여 넣고 **Commit changes**를 누릅니다.
5. `gitleaks.yml`도 같은 방법으로 `.github/workflows/gitleaks.yml`에 만듭니다.

두 파일 모두 `.github/workflows/` 경로에 올라가면 Actions 탭에서 실행됩니다.
