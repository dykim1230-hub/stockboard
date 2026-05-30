# Stockboard AI Worklog

이 문서는 Claude, GPT, Codex 등 AI 도구가 작업한 변경 이력과 결정사항을 남기는 공용 작업 로그입니다.

## 작성 규칙

- 새 작업은 최신 항목을 위에 추가한다.
- 변경 파일, 확인한 명령, 남은 일을 짧게 남긴다.
- 단순한 코드 설명보다 “왜 그렇게 했는지”를 우선 기록한다.
- 비밀값은 절대 적지 않는다.

## 로그

### 2026-05-30 - Gemini JSON 파싱 오류 수정 및 배포 자동 점검 체계 구축

| 항목 | 내용 |
| --- | --- |
| 작업자 | Claude Sonnet 4.6 |
| 변경 파일 | `main.py`, `scripts/post-deploy.sh`, `docs/deploy-checklist.md`, `docs/ai-handoff.md` |
| 커밋 | `672c4ef`, `526cb77`, `b910dea` |

**1. Gemini JSON 파싱 오류 수정**
- 증상: 뉴스레터에 투자 의견·뉴스 요약 섹션 누락
- 원인: 503 × 2회 재시도 후 3번째 시도에서 응답은 받았으나 `re.search(r"\[.*\]", text, re.DOTALL)` greedy 매칭이 JSON 배열 뒤 설명 텍스트까지 포함 → `json.loads` Extra data 에러
- 수정: `_parse_first_json_array` 헬퍼 추가 — `json.JSONDecoder().raw_decode()`로 첫 번째 완전한 JSON 배열만 파싱, 나머지 무시
- 적용: `_gemini_stock_analysis`, `_gemini_summarize` 두 곳 모두 교체

**2. 배포 후 자동 점검 체계 구축**
- `scripts/post-deploy.sh`: API 엔드포인트 5개, 서버 시크릿 하드코딩 여부, `.env` git 추적 여부, Digest dry-run 자동 점검
- `docs/deploy-checklist.md`: 자동/수동 점검 항목 통합 체크리스트 (AI 에이전트 기준 포함)
- `docs/ai-handoff.md`: 작업 종료 체크리스트에 배포 점검 항목 추가
- 보안 점검 오탐 수정: Firebase Web SDK `apiKey`는 공개키라 정상. `.py` 파일만 서버 시크릿 검사하도록 변경

**3. 점검 결과**
- `bash scripts/post-deploy.sh`: 8/8 전부 통과
- 강제 발송(`?force=true`): checked=3, sent=3, failed=0 — 3명 전원 정상 수신 확인

---

### 2026-05-26 - 수신자별 뉴스레터 내용 불일치 버그 수정

| 항목 | 내용 |
| --- | --- |
| 작업자 | Claude Sonnet 4.6 |
| 변경 파일 | `main.py`, `docs/ai-handoff.md`, `docs/ai-worklog.md` |
| 커밋 | `b589375` |

**증상**
- 동일 시간에 발송된 뉴스레터가 수신자에 따라 투자 의견·뉴스 요약이 있는 경우와 없는 경우로 나뉨

**원인**
- `_run_digest_job`이 사용자를 순차 처리하면서 각 사용자마다 `_gemini_stock_analysis` 호출
- Gemini 무료 티어 RPM 제한으로 2번째 이후 사용자의 Gemini 호출이 rate limit에 걸려 빈 결과 반환
- 오류가 조용히 폴백되어 투자 의견·뉴스 요약 없이 메일 발송

**수정**
- `_gemini_stock_analysis`: 429/quota/rate 에러 감지 시 30초·60초 대기 후 최대 2회 재시도
- `_run_digest_job`: 2번째 사용자부터 Gemini 호출 전 10초 딜레이 추가 (예방적 조치)

**검증**
- 3명 강제 발송 → `sent: 3, failed: 0` 확인

---

### 2026-05-26 - 뉴스레터 AI 요약 기능 추가 및 구조 개편

| 항목 | 내용 |
| --- | --- |
| 작업자 | Claude Sonnet 4.6 |
| 변경 파일 | `main.py`, `requirements.txt`, `docs/ai-handoff.md`, `docs/ai-worklog.md` |
| 커밋 | `00845be`, `2fee46e`, `c3d7f87`, `eec2259`, `0568052`, `62c595f` |

**1. Gemini AI 뉴스 요약 기능 추가**
- `google-genai` 패키지 추가 (구버전 `google-generativeai` 대신 신규 SDK 사용)
- Render 환경변수에 `GEMINI_API_KEY` 추가 (Google AI Studio 신규 프로젝트로 발급)
- 모델: `gemini-2.5-flash` (신규 계정은 `gemini-2.0-flash` 사용 불가)
- `_gemini_stock_analysis()`: 종목별 투자 의견(5문장) + 기사별 뉴스 요약(4문장) 한 번에 생성

**2. 뉴스레터 구조 전면 개편**
- 기존: 일반 경제 헤드라인 섹션 + 종목별 시세/뉴스 링크 나열
- 변경: 종목별로 `종목명·현재가·등락 → 투자 의견 → 뉴스 기사별 요약 → 링크` 구조
- 종목명 바로 옆에 현재가·등락 한 줄 배치 (가독성 개선)
- 투자 의견: 파란 박스, 소제목 구분
- 뉴스 요약: 기사별 개별 요약, 소제목 구분

**3. 강제 발송 기능 추가**
- `POST /api/cron/digest?force=true` — 시간 불일치·중복 발송 체크 무시하고 전체 회원 즉시 발송
- 기본값 `False`이므로 기존 cron 발송 동작에 영향 없음

**결정 사항**
- 일반 경제 헤드라인 섹션(`_fetch_headline_news`, `_gemini_summarize`, `_build_headline_section`) 코드는 보존하되 `_build_digest_html`에서 호출 제거. 추후 재활용 가능
- 소스 다양성: 매일경제 RSS + Google News 경제 헤드라인 RSS 조합, 소스별 최대 2개 제한

---

### 2026-05-19 - 버그 수정 및 성능 개선

| 항목 | 내용 |
| --- | --- |
| 작업자 | Claude Sonnet 4.6 |
| 변경 파일 | `index.html`, `main.py`, `docs/ai-handoff.md`, `docs/ai-worklog.md` |
| 작업 환경 | macOS, SSH 키 신규 설정 후 GitHub push |

**1. 메일 다이제스트 미발송 원인 2건 수정**
- Render 무료 티어 cold start 문제 → cron-job.org에 keepalive job 추가(`/api/market` 5분마다 GET). UptimeRobot 없이 cron-job.org만으로 서버 상시 기동 유지
- cron-job.org의 digest job `Enable job` 토글이 꺼져 있었음 → 활성화

**2. 초기 로딩 성능 개선**
- React/ReactDOM 개발 빌드(5.6MB) → 프로덕션 빌드(1.2MB)로 교체
- `/api/market` 백엔드: 지수 5개 순차 yfinance 조회 → `ThreadPoolExecutor` 병렬 조회
- `/api/quotes` 배치 엔드포인트 신규 추가 — 즐겨찾기 종목 시세를 1회 호출로 일괄 조회
- `FavoriteCard`, `MobilePriceCard`: 개별 quote 호출 제거 → 상위 App에서 배치 결과 prop으로 전달

**3. 뉴스 최신순 정렬**
- `_google_news_rss`: 기사 반환 전 `pubDate` 기준 내림차순 정렬 추가
- `email.utils.parsedate_to_datetime` 사용, 파싱 실패 시 `datetime.min`으로 안전 처리

**4. 관리자 회원 목록 미표시 버그 수정**
- `admin_list_users`에서 `u.user_metadata.last_sign_in_time`, `creation_time` 사용 → Firebase Admin SDK 실제 속성명 `last_sign_in_timestamp`, `creation_timestamp`으로 수정
- 예외 처리 추가 및 프론트 에러 메시지 실제 오류 내용 표시로 개선

**5. GitHub SSH 인증 설정**
- HTTPS 인증 만료로 push 불가 → ed25519 SSH 키 신규 생성, GitHub 등록, remote URL SSH로 변경

| 확인 | 내용 |
| --- | --- |
| 배포 | Firebase Hosting 배포 완료, GitHub push → Render 자동 배포 |
| 커밋 | `eb19e29`, `0cc0923`, `5882bc9`, `b7bccb2` |

### 2026-05-16 - UI 전면 개선 및 시장 현황 기능 추가

| 항목 | 내용 |
| --- | --- |
| 작업자 | Claude |
| 변경 파일 | `index.html`, `style.css`, `main.py` |
| 목적 | 모바일 UI 어색함 해소, 데스크탑 레이아웃 개선, 시장 지수 현황 화면 추가 |
| 결정 1 | 시장 현황(S&P 500, NASDAQ, KOSPI, KOSDAQ, 원/달러)을 로그인 전 누구나 볼 수 있는 첫 화면으로 구현. 백엔드 `/api/market` 엔드포인트 추가(yfinance, 5분 캐시) |
| 결정 2 | 시장 현황 카드 → 얇은 **티커 바** 스타일로 변경 (Bloomberg 참조). 박스 카드보다 훨씬 자연스럽고 공간 효율적 |
| 결정 3 | 데스크탑에서 차트 + 뉴스를 단일 컬럼 → `1024px` 이상에서 **2컬럼(1.4fr:1fr)** 레이아웃으로 변경 |
| 결정 4 | 모바일 헤더: 긴 버튼 → 원형 아이콘 버튼(40px) 한 줄 배치. `font-size:0`으로 텍스트 숨김, `material-symbols-outlined` 아이콘만 표시 |
| 결정 5 | 즐겨찾기 선택: 모바일에서 가로 스크롤 카드 → **커스텀 바텀시트 드롭다운**으로 교체. 사파리 native select UI를 피하기 위해 React 컴포넌트(`CustomSelect`)로 직접 구현. 선택 시 현재가·등락 카드(`MobilePriceCard`) 표시 |
| 결정 6 | 로그인 화면: 자물쇠 아이콘 단순 배너 → 아이콘 + 제목 + 설명 + CTA 버튼 구조로 개선 |
| 결정 7 | 뉴스 섹션에 `glass-panel` 클래스 추가 (차트 섹션과 시각적 일관성) |
| 결정 8 | 메일 다이제스트 HTML에 "대시보드 바로가기" 버튼 2개 추가 (상단, 하단) |
| 배포 | Firebase Hosting 배포 완료, GitHub main 푸시 → Render 자동 배포 |
| 다음 작업 | 모바일 실기기 추가 확인, 애널리스트 의견 기능(FMP 유료 또는 Claude API), 기술적 차트 지표 추가 검토 |

### 2026-05-16 - 새 컴퓨터 환경 셋업

| 항목 | 내용 |
| --- | --- |
| 작업자 | Claude |
| 목적 | 다른 컴퓨터에서 동일 프로젝트 이어받기 |
| 확인 내용 | git 2.53, node 24.14, npm 11.9, firebase-tools 15.17 모두 설치됨 확인 |
| 조치 | `git clone`, `git config --global user.name/email` 설정, Firebase 로그인 상태 확인 (portfolio-4ffcf 연결됨) |
| 결론 | 로컬 Python 환경 없이도 코드 수정 → GitHub push → Render 자동 배포 방식으로 백엔드 작업 가능 |

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
