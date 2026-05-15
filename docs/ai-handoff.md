# Stockboard AI Handoff

이 문서는 다음 AI 도구가 바로 이어서 작업할 수 있도록 현재 상태와 다음 작업만 짧게 정리하는 인수인계 문서입니다.

## 현재 상태

| 항목 | 상태 |
| --- | --- |
| 기본 대시보드 | 구현됨 |
| Firebase Auth 로그인 | 구현됨 |
| Firestore 즐겨찾기 저장 | 구현됨 |
| 종목 검색/시세/차트 | 구현됨 |
| Google News RSS 뉴스 | 구현됨 |
| 관리자 패널 | 구현됨 |
| 회원별 메일 다이제스트 UI | 구현됨 |
| 메일 다이제스트 백엔드 | 구현됨 |
| Render Cron Job | 설정 및 실행 결과 확인 필요 |
| Resend 실제 발송 | 검증 필요 |
| Cron 진단 응답 | 구현됨 |

## 다음 작업 후보

1. Render 환경변수 확인
   - `RESEND_API_KEY`
   - `MAIL_FROM`
   - `CRON_SECRET`
   - `FIREBASE_SERVICE_ACCOUNT`
   - `ADMIN_UIDS`

2. Render Cron Job 생성 또는 동작 확인
   - 매시 정각 `/api/cron/digest` 호출
   - `x-cron-secret` 헤더 포함
   - `dry_run=true`로 대상자 계산 검증
   - `include_details=true`로 제외 사유 확인

3. 실제 메일 발송 테스트
   - 테스트 사용자에서 `emailDigest.enabled=true`
   - 현재 Asia/Seoul hour와 사용자 설정 hour 일치
   - 하루 1회 중복 발송 방지 확인

4. 수신 해지/설정 변경 링크 설계
   - 메일 본문에서 계정 설정 화면으로 이동
   - 필요 시 unsubscribe 전용 토큰 방식 검토

## 작업 시작 체크리스트

- [ ] `docs/ai-context.md`를 읽었다.
- [ ] 이 파일의 `현재 상태`와 `다음 작업 후보`를 확인했다.
- [ ] `git status --short`로 사용자 변경사항을 확인했다.
- [ ] 필요한 파일만 좁게 읽고 수정 범위를 정했다.

## 작업 종료 체크리스트

- [ ] 변경한 파일을 요약했다.
- [ ] 테스트 또는 확인 명령 결과를 기록했다.
- [ ] 다음 작업자가 이어받을 내용을 이 파일에 갱신했다.
- [ ] 중요한 결정사항은 `docs/ai-worklog.md`에 추가했다.

## 주의사항

- 사용자가 만들었거나 다른 AI가 만든 변경사항을 임의로 되돌리지 않는다.
- 배포 설정, Firebase 프로젝트, Render 서비스, 도메인 설정 변경은 사용자 확인 후 진행한다.
- API 키, service account JSON, cron secret 값은 문서에 직접 기록하지 않는다.
- 현재 프로젝트는 간단한 정적 프론트 구조다. Vite 등으로 전환하는 작업은 별도 범위로 잡는다.

## 마지막 인수인계

| 항목 | 내용 |
| --- | --- |
| 날짜 | 2026-05-15 |
| 작성자 | Codex |
| 내용 | 메일 다이제스트 미발송 원인 확인을 위해 cron 진단 응답을 추가했다. `dry_run=true&include_details=true`로 제외 사유와 Resend 설정 여부를 볼 수 있다. |
| 다음 우선순위 | 배포 후 실제 `CRON_SECRET`으로 dry run 호출하여 `skip_reasons`, `resend_configured`, `eligible` 값을 확인 |
