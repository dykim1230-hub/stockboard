# Stockboard AI Worklog

이 문서는 Claude, GPT, Codex 등 AI 도구가 작업한 변경 이력과 결정사항을 남기는 공용 작업 로그입니다.

## 작성 규칙

- 새 작업은 최신 항목을 위에 추가한다.
- 변경 파일, 확인한 명령, 남은 일을 짧게 남긴다.
- 단순한 코드 설명보다 “왜 그렇게 했는지”를 우선 기록한다.
- 비밀값은 절대 적지 않는다.

## 로그

### 2026-05-15 - 메일 다이제스트 cron 진단 응답 추가

| 항목 | 내용 |
| --- | --- |
| 작업자 | Codex |
| 변경 파일 | `main.py`, `test_digest_cron.py`, `requirements.txt`, `docs/email-digest-setup.md`, `docs/ai-handoff.md` |
| 목적 | cron은 실행되지만 실제 메일이 발송되지 않는 상황에서 제외 사유와 설정 상태를 빠르게 확인하기 위함 |
| 결정 | `/api/cron/digest`에 `include_details` 쿼리를 추가하고, 응답에 `current_hour`, `resend_configured`, `skip_reasons`를 포함 |
| 확인 | `.venv/bin/python -m unittest test_digest_cron.py` 실행 필요 |
| 다음 작업 | 배포 후 실제 secret으로 `dry_run=true&include_details=true` 호출하여 대상자와 제외 사유 확인 |

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
