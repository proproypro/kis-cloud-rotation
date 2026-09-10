# KIS 섹터 순환매 자동매매 (클라우드)

한국투자증권 KIS OpenAPI **모의투자** 계좌에서 국장 섹터 순환매 스윙을 자동 실행.
GitHub Actions로 서버 없이 무인 운영.

## 동작
- **매주 월 10:00(KST)**: 선도 섹터(20일 모멘텀 최상위) 내 강한 종목 3개로 리밸런싱. 코스피 200일선 하회 시 현금.
- **평일 15:40(KST)**: 계좌 스냅샷 기록 → `data/portfolio_history.json` 자동 커밋 (자산곡선).

## 설정 (한 번만)
1. GitHub 저장소 생성 후 이 코드 push
2. **Settings → Secrets and variables → Actions** 에 등록:
   - `KIS_APP_KEY`, `KIS_APP_SECRET`, `KIS_ACCOUNT_NO`
3. Actions 탭에서 수동 실행(workflow_dispatch)으로 첫 테스트

## 주의
- 모의투자 전용. 실제 돈 아님.
- KIS OpenAPI가 GitHub 러너(해외 IP)에서 되는지 첫 실행으로 확인.
- 비밀키는 절대 커밋 금지 (.gitignore 처리됨).
