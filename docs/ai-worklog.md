# Stockboard AI Worklog

이 문서는 Claude, GPT, Codex 등 AI 도구가 작업한 변경 이력과 결정사항을 남기는 공용 작업 로그입니다.

## 작성 규칙

- 새 작업은 최신 항목을 위에 추가한다.
- 변경 파일, 확인한 명령, 남은 일을 짧게 남긴다.
- 단순한 코드 설명보다 “왜 그렇게 했는지”를 우선 기록한다.
- 비밀값은 절대 적지 않는다.

## 로그

### 2026-05-15 - 메일 다이제스트 실제 발송 성공

| 항목 | 내용 |
| --- | --- |
| 작업자 | Codex/사용자 |
| 관련 파일 | `main.py`, `docs/email-digest-setup.md`, `docs/ai-handoff.md`, `docs/ai-worklog.md` |
| 배경 | cron-job.org에서 호출 시 403이 발생했고, 이후 `CRON_SECRET` 교체 및 양쪽 설정 동기화가 필요했음 |
| 조치 | Render Web Service의 `CRON_SECRET`과 cron-job.org custom header `x-cron-secret`을 새 값으로 맞춤 |
| 확인 | cron-job.org 테스트 호출 성공 확인 |
| 실제 발송 | 사용자 발송 시간을 테스트 가능한 시간으로 맞춘 뒤 실제 메일 발송 성공 |
| 수신 확인 | 고객이 메일을 받은 것까지 확인됨 |
| 결론 | 회원별 선택 시간 기반 메일 다이제스트 기능은 운영 경로에서 정상 동작 확인됨 |
| 남은 일 | 노출된 기존 `CRON_SECRET` 폐기 상태 유지, 수신 해지/설정 변경 링크 추가, 실패 로그/audit 보강 검토 |

### 2026-05-15 - 모바일 UI 1차 최적화 및 배포

| 항목 | 내용 |
| --- | --- |
| 작업자 | Codex |
| 변경 파일 | `style.css` |
| 목적 | 모바일 화면에서 헤더, 버튼, 카드, 차트, 뉴스 리스트, 모달이 깨지는 문제를 완화하기 위함 |
| 결정 | CSS 반응형 규칙만으로 1차 대응했다. 구조 변경 없이 `@media (max-width: 768px)`, `@media (max-width: 420px)`를 추가했다. |
| 주요 변경 | 헤더 세로 배치, 버튼 그리드화, 즐겨찾기 카드 모바일 폭 조정, 차트 높이 축소, 기간 선택 스크롤 대응, 뉴스 리스트 압축, 모달 하단 시트화, 테이블 가로 스크롤 대응 |
| 확인 | `git diff --check` 통과. 로컬 서버 화면 확인은 포트 바인딩 권한 문제로 생략하고 사용자가 배포본에서 직접 확인하기로 함 |
| 배포 | `a44729c Improve mobile layout` 커밋을 `origin/main`에 푸시 완료 |
| 다음 작업 | 사용자가 모바일에서 확인 후 깨지는 화면 스크린샷을 기준으로 추가 조정 |

### 2026-05-15 - 메일 다이제스트 cron 진단 응답 추가

| 항목 | 내용 |
| --- | --- |
| 작업자 | Codex |
| 변경 파일 | `main.py`, `test_digest_cron.py`, `requirements.txt`, `docs/email-digest-setup.md`, `docs/ai-handoff.md` |
| 목적 | cron은 실행되지만 실제 메일이 발송되지 않는 상황에서 제외 사유와 설정 상태를 빠르게 확인하기 위함 |
| 배경 | 회원이 선택한 시간에 메일 다이제스트를 보내는 기능을 구현했으나 실제 메일이 오지 않아 원인 확인이 필요했음 |
| 변경 내용 | `/api/cron/digest`에 `include_details` 쿼리를 추가하고, 응답에 `current_hour`, `resend_configured`, `skip_reasons`, 마스킹된 대상자 상세를 포함 |
| 방어 처리 | 잘못된 `emailDigest.hour` 값 때문에 전체 cron이 중단되지 않도록 `_parse_digest_hour`를 추가 |
| 테스트 | `.venv/bin/python -m unittest test_digest_cron.py` 실행, 5개 테스트 통과 |
| 배포 | `410f7d6 Add digest cron diagnostics` 커밋을 `origin/main`에 푸시 완료 |
| dry run 결과 | `checked=2`, `eligible=0`, `sent=0`, `skipped=2`, `failed=0`, `resend_configured=true`, `current_hour=17` |
| 확인된 미발송 원인 | Resend 설정 문제는 아니었고, 활성 사용자의 `emailDigest.hour`가 `7`로 저장되어 현재 Asia/Seoul `17시`와 맞지 않아 `hour_mismatch`로 제외됨 |
| 운영 메모 | 실제 스케줄러는 Render Cron Job이 아니라 cron-job.org 사용 중. cron-job.org custom header의 `x-cron-secret`이 Render Web Service의 `CRON_SECRET`과 일치해야 함 |
| 보안 메모 | 대화 중 기존 `CRON_SECRET` 값이 노출되어 Render와 cron-job.org 양쪽에서 새 값으로 교체 완료 |
| 결과 | 이후 cron-job.org 테스트 성공 및 실제 메일 발송/고객 수신까지 확인됨 |
| 다음 작업 | 실패 시 cron-job.org 실행 로그, Render 로그, Firestore `emailDigest.lastError`, Resend 로그 순서로 확인 |

### 2026-05-15 - AI 공용 컨텍스트 문서 추가

| 항목 | 내용 |
| --- | --- |
| 작업자 | Codex |
| 변경 파일 | `docs/ai-context.md`, `docs/ai-handoff.md`, `docs/ai-worklog.md` |
| 목적 | Claude와 GPT를 번갈아 사용할 때 프로젝트 상태와 작업 인수인계를 같은 기준으로 공유하기 위함 |
| 결정 | 저장소 내부 `docs/`에 공용 문서를 두고, 작업 시작 전 `ai-context`와 `ai-handoff`를 읽는 방식으로 운영 |
| 확인 | 기존 `docs/notion-project-log.md`, `docs/email-digest-setup.md` 내용을 참고해 구성 |
| 다음 작업 | 실제 기능 작업 후 매번 `ai-handoff.md`와 이 로그를 갱신 |

## 템플릿

### YYYY-MM-DD - 작업 제목

| 항목 | 내용 |
| --- | --- |
| 작업자 | Claude/GPT/Codex/사용자 |
| 변경 파일 |  |
| 목적 |  |
| 결정 |  |
| 확인 |  |
| 다음 작업 |  |
