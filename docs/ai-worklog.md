# Stockboard AI Worklog

이 문서는 Claude, GPT, Codex 등 AI 도구가 작업한 변경 이력과 결정사항을 남기는 공용 작업 로그입니다.

## 작성 규칙

- 새 작업은 최신 항목을 위에 추가한다.
- 변경 파일, 확인한 명령, 남은 일을 짧게 남긴다.
- 단순한 코드 설명보다 “왜 그렇게 했는지”를 우선 기록한다.
- 비밀값은 절대 적지 않는다.

## 로그

### 2026-06-21 - 차트 black screen 수정 + 캔들스틱 복원

| 항목 | 내용 |
| --- | --- |
| 작업자 | Claude Sonnet 4.6 |
| 변경 파일 | `index.html` |
| 커밋 | `3fc857f` (Babel 고정), `5a75ae4` (캔들스틱 복원) |

**1. Black screen 원인 분석 및 수정**
- 증상: 사이트 접속 시 화면 전체가 검은색으로만 보임
- 원인: `@babel/standalone` 버전 미고정 → 최신 버전이 JSX 변환 출력을 ES module 형식으로 변경 → `import` 구문이 일반 `<script>` 컨텍스트에서 허용되지 않아 Babel이 appendChild 실패
- 에러: `VM66:6 Uncaught SyntaxError: Failed to execute 'appendChild' on 'Node': Cannot use import statement outside a module`
- 수정: `@babel/standalone@7.23.10`으로 버전 고정
- 교훈: 이전 black screen(5311dbf 커밋)도 이 Babel 버전 문제였을 가능성 높음. 커스텀 플러그인 코드 자체는 문제 없었음

**2. 캔들스틱 차트 복원**
- `chartjs-chart-financial`은 Chart.js 4.x UMD와 비호환(플러그인 로드 시 `window.Chart.BarController` undefined 크래시) → 영구 제거
- 대신 Chart.js 내장 canvas API로 `afterDatasetsDraw` 커스텀 플러그인 구현
- 데이터셋: `type: 'line'`에 `_ohlc` 필드로 OHLC 데이터 전달, 투명 선으로 x/y 스케일만 잡고 실제 캔들은 플러그인이 직접 그림
- 상승(종가≥시가): 초록 `#10b981`, 하락: 빨강 `#ef4444`
- y축: 고가/저가 기준으로 `min * 0.998`, `max * 1.002` 범위 설정
- 툴팁: dataset[0] 호버 시 시가/고가/저가/종가 4줄 표시

**3. 백업 복구 과정에서 OnboardingFlow 누락 발견**
- `index_backup_20260612.html`이 당일 세션 초기 백업 → OnboardingFlow, 추천 랜딩 개선 등 2026-06-12 작업 내용 미포함
- 현재 배포 코드에서 OnboardingFlow 컴포넌트 없음. 필요 시 `b22b1da` 커밋에서 복구 가능

### 2026-06-12 - ahdoyoon.site OAuth 설정 완료 + UX 개선 다수 + 온보딩 플로우 추가

| 항목 | 내용 |
| --- | --- |
| 작업자 | Claude Sonnet 4.6 |
| 변경 파일 | `index.html`, `style.css`, `main.py` |
| 백업 | `index_backup_20260612.html`, `main_backup_20260612.py` |
| 커밋 | `86389e5`, `a27f4b4`, `83e21e9`, `bcb2ce1`, `0e36c7a` |

**1. ahdoyoon.site Google OAuth 설정 완료**
- Google Cloud Console 승인된 리디렉션 URI: `https://ahdoyoon.site/__/auth/handler`, `https://portfolio-4ffcf.firebaseapp.com/__/auth/handler` 등록
- Google Cloud Console 승인된 JavaScript 원본: `https://ahdoyoon.site` 추가
- Firebase Console > Authentication > Authorized domains: `ahdoyoon.site` 추가
- 결과: `ahdoyoon.site` 도메인에서도 Google 소셜 로그인 정상 작동

**2. 문의 메일 미수신 문제 해결**
- 원인: `CONTACT_ADMIN_EMAIL` 환경변수 미설정 → `MAIL_FROM`(`noreply@ahdoyoon.site`)으로 발송 → 받는 사람 없음
- 해결: Render 환경변수에 `CONTACT_ADMIN_EMAIL` 추가 (실제 수신 이메일 주소 설정)
- 확인: Resend 대시보드에서 TO 주소 정상 확인

**3. 경제일정 롤 레이아웃 CSS 강화**
- 현상: 금주 일정이 1줄이어야 하는데 2줄로 표시되고 폰트 달라짐
- 수정: `flex-direction: row; flex-wrap: nowrap` 명시, `min-width: 0` 추가, `white-space: nowrap` 자식 요소에도 명시, `font-family: var(--font-main)` 지정
- 파일: `style.css`

**4. 차트 이동평균선 레이블 한국어 변경**
- MA5 → 5일선, MA20 → 20일선, MA60 → 60일선
- 차트 범례, 버튼 UI, 랜딩 기능 소개 문구 모두 변경
- 파일: `index.html`

**5. 뉴스레터 추천하기 버튼 추가**
- 뉴스레터 이메일 하단에 `📨 친구에게 MarketPulse 추천하기` 버튼 추가
- href: `https://ahdoyoon.site/invite?ref={uid}` (uid 기반 추천 링크)
- 기존 단순 공유 섹션을 버튼 형태로 교체, Gmail/Outlook 호환 인라인 스타일만 사용
- 이메일 내 URL 전체 `portfolio-4ffcf.web.app` → `ahdoyoon.site` 업데이트
- 파일: `main.py`

**6. 랜딩 페이지 개선 + 가입 후 온보딩 플로우 추가**
- `?ref=` URL 파라미터 읽어 `sessionStorage.referrer_uid` 저장
- ref 있을 때 히어로 문구 "지인이 매일 아침 받아보는 주식 브리핑입니다", CTA "나도 받아보기" 조건부 렌더링
- 샘플 뉴스레터 목업 섹션 추가 (삼성전자 예시, "샘플" 배지)
- 기능 소개 카드 4개 desc 사용자 상황 문구로 교체
- 기능 카드 아래 CTA 버튼 재배치 추가
- `OnboardingFlow` 컴포넌트 신규 추가 (STEP1 종목 등록 / STEP2 수신 시간 / STEP3 완료)
- 가입 완료 후 메인 대신 온보딩으로 전환, STEP3 완료 시 Firestore에 favorites / emailDigest.hour / referredBy 저장
- `AuthModal`에 `onSignUp` 콜백 prop 추가, 이메일·Google 가입 시 각각 호출
- 파일: `index.html`

**결정사항**
- 추천 랜딩 페이지(`/invite`) 자체는 미구현 — Firebase Hosting 모든 경로 → index.html rewrite이므로 링크 클릭 시 랜딩 페이지로 이동은 되나 추천인 처리 로직은 sessionStorage 저장 방식으로 처리됨
- 온보딩 완료 후 favorites/emailDigest는 Firestore 직접 저장 후 App state에도 반영

---

### 2026-06-11 (3) - 시장현황 경제일정 통합 + 가격 차트 캔들스틱 전환

| 항목 | 내용 |
| --- | --- |
| 작업자 | Claude Sonnet 4.6 |
| 변경 파일 | `index.html`, `style.css`, `main.py` |
| 백업 | `index_backup_20260611.html`, `main_backup_20260611.py` |
| 커밋 | `3ea2c70` |

**1. 시장현황(MarketOverview)에 경제일정 통합**
- 기존 별도 패널이었던 "📅 이번 주 경제 일정"(`EconomicCalendar`/`EcCalBoundary`/`ImpactDots`)을 제거하고, 시장현황 패널 하단에 통합
- `/api/economic-calendar?weeks=2`를 MarketOverview에서 직접 fetch
- 처음에는 한 줄씩 나열 → 사용자 피드백으로 칩(pill) 형태 + 아이콘으로 변경 → 다시 사용자 피드백으로 최종적으로 일정이 여러 개일 때 3초 간격으로 위로 슬라이드되며 한 줄씩 롤링되는 형태로 확정 (`market-econ-roll`, `econRollIn` keyframe)
- 비로그인 사용자도 시장현황은 보이므로 경제일정도 자동으로 노출 범위 확대됨

**2. 가격 차트 라인 → 캔들스틱 전환**
- 사용자 요청: "종목 가격 그래프를 캔들 그래프로 변경"
- `main.py`의 `/api/chart`가 `1. open`/`2. high`/`3. low`도 반환하도록 수정 (기존엔 close/volume만)
- `index.html`: `chartjs-chart-financial` + `chartjs-adapter-date-fns` CDN 추가, `ChartSection`의 메인 데이터셋을 `type:'candlestick'`(상승 초록/하락 빨강)으로 교체
- MA5/MA20/MA60/볼린저밴드는 `type:'line'` 오버레이로 유지, x축은 `category` → `time` 스케일로 변경 (모든 데이터셋 `{x: timestamp, ...}` 형식)
- 툴팁에 시가/고가/저가/종가 표시하도록 콜백 커스터마이징
- 거래량 바 차트는 기존 category 라벨 그대로 사용 (변경 없음)
- 배포 후 `/api/chart?symbol=...` 응답에 OHLC 필드 포함 확인 완료

**별도 진행 중 이슈 (미해결)**
- 사용자가 "관리자에게 메일 보내기" 문의 폼이 "전송완료로 뜨는데 실제 메일은 오지 않는다"고 보고
- `/api/contact`는 `{"ok":true}`(200) 반환 — Resend API 호출 자체는 성공(<400)
- 코드(`_send_resend_email`, `/api/contact`)는 정상으로 보임 — `CONTACT_ADMIN_EMAIL`/`MAIL_FROM` 수신 주소 또는 Resend 대시보드의 실제 발송/차단 로그 확인 필요 (사용자에게 Resend 대시보드 확인 요청, 아직 회신 없음)

### 2026-06-11 - 경제지표 캘린더 데이터 소스 3종 점검 및 버그 수정

| 항목 | 내용 |
| --- | --- |
| 작업자 | Claude Sonnet 4.6 |
| 변경 파일 | `main.py` |
| 백업 | `main_backup_20260611.py` |

**배경**
- 2026-06-08에 경제지표 캘린더 기능(`fetch_bls_calendar`, `fetch_bok_calendar`, `fetch_fomc_calendar`, `/api/cron/update-calendar`, `/api/economic-calendar`)이 구현됐으나 `docs/ai-handoff.md`에는 "다음 작업 1순위"로 남아있어 상태 점검 겸 실제 동작 여부를 로컬에서 검증함

**1. FOMC 파싱 버그 수정**
- 증상: `fetch_fomc_calendar()`가 항상 빈 배열 반환
- 원인: `.fomc-meeting__date`에는 "27-28" 같은 일자만 있고 월(`January` 등)은 별도 `.fomc-meeting__month` div에 있음 → 기존 코드는 date 텍스트에서만 `[A-Za-z]+\s+\d+` 정규식을 찾았기 때문에 항상 매칭 실패 → 모든 회의가 스킵됨
- 수정: `.fomc-meeting__month`에서 월, `.fomc-meeting__date`에서 일자를 각각 읽어 조합
- 검증: 2026-06-17, 2026-07-29 FOMC 일정 정상 반환 확인

**2. BOK 캘린더 데이터 소스 교체**
- 증상: 기존 URL(`B0000338?menuNo=200069&rssYn=Y`)이 RSS가 아닌 "지역경제보고서" 게시판 HTML을 반환 → `feedparser` 0건
- 원인: BOK 보도자료 RSS(`P0000559/news.rss`, `B0000552/news.rss`)는 모두 *과거* 발표 이력만 제공 → 미래 일정 캘린더에 사용 불가
- 수정: BOK 공식 "통화정책방향 결정회의 일정" 페이지(`crncyPolicyDrcMtg/listYear.do?mtgSe=A&menuNo=200755`)를 스크래핑하여 `BOK_RATE`(기준금리 결정) 미래 일정 수집
- `KR_CPI`(소비자물가지수)는 한국은행이 아닌 통계청(KOSIS) 발표 항목이라 이번 작업 범위에서 제외 (사용자 확인, INDICATOR_META 항목은 보존)
- 검증: 2026-07-16 기준금리 결정일 정상 반환 확인

**3. BLS iCalendar 403 — 호출 제외 처리**
- `fetch_bls_calendar()`는 2026-06-08 커밋(`f152871`)에서 Chrome User-Agent를 추가했지만 이 환경과 Render 양쪽 모두 여전히 403 (Akamai `Access Denied`)
- `www.bls.gov`의 모든 페이지(메인 페이지 포함)가 동일하게 403 → User-Agent 문제가 아니라 Akamai의 IP 평판 기반(데이터센터 IP) 차단으로 확인. `api.bls.gov`(다른 호스트)는 200 정상
- 함수 자체는 보존하되 `update_economic_calendar`의 수집 함수 목록에서 제외 → 매주 불필요한 403 요청 방지
- 향후 FRED(세인트루이스 연은) Release Dates API로 대체 가능 (CPI release_id=10, PPI=46, Employment Situation=50, `FRED_API_KEY` 필요) — `docs/ai-handoff.md` 다음 작업 후보 참고

---

### 2026-06-11 (2) - 경제지표 캘린더 배포·운영 개시 확인

| 항목 | 내용 |
| --- | --- |
| 작업자 | Claude Sonnet 4.6 |
| 변경 파일 | `main.py`, `docs/ai-handoff.md`, `docs/ai-worklog.md` |
| 커밋 | `4efdacc` (FOMC/BOK 수정) + 이번 커밋 (BLS 제외) |

**진행**
- `4efdacc` 푸시 → Render 자동 배포 완료 확인 (`GET /api/economic-calendar` 200 정상)
- cron-job.org에 `POST /api/cron/update-calendar` 잡 등록 (매주 월요일 00:00 UTC, `x-cron-secret` 헤더) 후 수동 실행
- 응답 `{"status":"ok","updated":3,"errors":[]}` — FOMC 2건(2026-06-17, 2026-07-29), BOK_RATE 1건(2026-07-16) 정상 수집
- Render 로그에서 `fetch_bls_calendar error: 403 Client Error: Forbidden` 확인 → BLS는 호출 목록에서 제외 (위 항목 참고)

**결정사항**
- 당분간 경제지표 캘린더는 FOMC(미국 금리결정), BOK_RATE(한국 기준금리)만 운영. 미국 CPI/PPI/고용지표는 FRED API 적용 전까지 보류

---

### 2026-06-08 (2) - 로그인 후 공백 화면 버그 수정, EconomicCalendar ErrorBoundary 추가

| 항목 | 내용 |
| --- | --- |
| 작업자 | Claude Sonnet 4.6 |
| 변경 파일 | `index.html` |
| 커밋 | `6a78e00`, `e180f66` |

**배경**
- EconomicCalendar 컴포넌트 추가 후 로그인 시 화면 전체가 공백이 되는 문제 발생
- 로그인 전 랜딩 페이지는 정상 표시, 로그인 후에만 증상 발생

**근본 원인 (commit `e180f66`)**
- 2026-06-05에 웹 AI 투자의견 기능(`/api/analysis`) 제거 시 ChartSection의 `analysis`·`analysisLoading` state는 삭제했으나, 해당 값을 렌더링하는 JSX 블록 22줄이 그대로 남아 있었음
- 로그인 전: `activeStock = null` → ChartSection이 early return하여 해당 JSX에 도달하지 않음 → 무증상
- 로그인 후: favorites 로드 → `activeStock` 설정 → ChartSection이 full render → 미정의 `analysisLoading` 참조 → ReferenceError → React 트리 전체 unmount → 공백 화면
- **수정:** ChartSection에서 stale analysis JSX 블록 완전 제거

**추가 작업 (commit `6a78e00`)**
- `EcCalBoundary` Error Boundary 클래스 컴포넌트 추가
- `EconomicCalendar`를 `EcCalBoundary`로 감싸 재활성화
- 렌더 에러 발생 시 앱 전체가 죽지 않고 해당 섹션만 null 반환
- `componentDidCatch`에서 에러를 콘솔에 출력하여 향후 디버깅 가능

**결정사항**
- EconomicCalendar는 현재 Firestore에 데이터 없음 → 섹션이 숨겨진 상태(return null)가 정상
- cron-job.org에 주간 캘린더 업데이트 잡 등록 후 실제 데이터 확인 예정

---

### 2026-06-08 - Gemini 모델 2.5-flash-lite 고정, 뉴스 요약 재시도 로직 추가

| 항목 | 내용 |
| --- | --- |
| 작업자 | Claude Sonnet 4.6 |
| 변경 파일 | `main.py` |
| 커밋 | `8aebff1` |

**배경**
- 뉴스 요약·투자 의견이 뉴스레터에서 계속 누락되는 문제
- Gemini 1.5/2.0-flash 모델이 2026년 상반기 중 서비스 종료되어 폴백 시 404 발생
- `_gemini_summarize`에 재시도 로직이 없어 1회 실패 즉시 빈 값 반환

**변경 내용**

1. 모델 고정: `gemini-2.5-flash-lite`
   - 뉴스레터용 API 호출은 하루 1~2회로 RPD 여유 충분
   - `_gemini_summarize`: `gemini-1.5-flash` → `gemini-2.5-flash-lite`
   - `_gemini_stock_analysis` 기본값: `gemini-2.5-flash` → `gemini-2.5-flash-lite`

2. `_gemini_summarize` 재시도 로직 추가 (기존 0회 → 최대 3회)
   - 빈 응답, JSON 파싱 실패, rate limit(429/503) 모두 재시도
   - `retryDelay` 파싱 또는 지수 백오프(최대 60s) 적용

3. `_gemini_stock_analysis` 폴백 모델 정리
   - 기존: `[gemini-2.0-flash, gemini-1.5-flash]` (종료된 모델)
   - 변경: `[gemini-2.5-flash]` (lite 2회 실패 시 full로 전환)

**결정사항**
- gemini-1.5/2.0-flash 모두 2026년 서비스 종료 확인 — 폴백에서 완전 제거
- Gemini 2.5 Flash-Lite 무료 티어: RPD 1,000~5,000, 뉴스레터용으로 충분

---

### 2026-06-05 - 웹 AI 의견 제거, 문의 폼 추가, Gemini 폴백 개선

| 항목 | 내용 |
| --- | --- |
| 작업자 | Claude Sonnet 4.6 |
| 변경 파일 | `main.py`, `index.html`, `test_digest_cron.py`, `docs/ai-context.md`, `docs/ai-handoff.md`, `docs/ai-worklog.md`, `docs/notion-project-log.md` |
| 커밋 | `e394a30` |

**1. 웹사이트 AI 투자의견·뉴스요약 제거**
- 원인: 웹 화면에서 종목 조회 시마다 `_gemini_chart_comment` 호출 → 뉴스레터용 Gemini 일일 쿼터 소모
- 수정: `_gemini_chart_comment` 함수 및 `GET /api/analysis` 엔드포인트 삭제
- 프론트: `analysis` state, fetch useEffect, "AI 투자 의견" 섹션 전체 제거
- 효과: Gemini 쿼터 전량 뉴스레터 전용으로 집중

**2. 문의 폼 추가 (푸터 영역)**
- `POST /api/contact` 엔드포인트 추가 (FastAPI, pydantic BaseModel)
- IP당 10분에 최대 3회 rate limit (in-memory dict)
- 수신 이메일: `CONTACT_ADMIN_EMAIL` env var, 없으면 `MAIL_FROM` 사용
- 프론트: `ContactModal` (이름/이메일/제목/내용, 글자수 표시, 성공 화면) + `Footer` 컴포넌트
- 임포트 추가: `Request` (fastapi), `BaseModel` (pydantic)

**3. Gemini 폴백 모델 개선**
- 기존: gemini-2.5-flash → gemini-2.0-flash (2단계)
- 변경: gemini-2.5-flash × 2 → gemini-2.0-flash → gemini-1.5-flash (3단계)
- 쿼터 소진(429+quota) 감지 시 대기 없이 즉시 다음 모델로 전환
- 503 응답의 `retryDelay` 값을 파싱해 API 권장 대기시간 준수
- 적용: `_gemini_stock_analysis` (뉴스레터 전용)

**4. 기타**
- `test_digest_cron.py`: `force=False` 누락 테스트 2개 수정
- Render 리모트와 rebase 충돌 해소: Search Grounding 설정 보존 + 새 폴백 로직 적용

**결정사항**
- 웹 AI 의견은 쿼터 소진 시 어차피 공란 → 제거해도 UX 손실 없음. 뉴스레터 품질이 더 중요
- gemini-1.5-flash: 이전 로그(2026-06-01)에서 이 계정 v1beta 404로 기록했으나, 재추가해 운영 환경에서 실제 작동 여부 확인 예정

---

### 2026-06-03 - UI 개선 5종, 버그 수정 2건, Gemini Google Search Grounding

| 항목 | 내용 |
| --- | --- |
| 작업자 | Claude Sonnet 4.6 |
| 변경 파일 | `index.html`, `style.css`, `main.py`, `docs/ai-handoff.md`, `docs/ai-worklog.md` |

**1. UI 개선 5종**
- 페이지 타이틀 변경: `MarketPulse — AI 주식 브리핑`
- 즐겨찾기 비어있을 때 온보딩 패널 표시 (`.fav-onboarding`)
- AI 투자의견 위치: 캔버스 아래 → 캔버스 위로 이동 (먼저 보이도록)
- 기술지표 토글 버튼에 툴팁 추가 (`.indicator-tooltip`, hover/tap 표시)
- 즐겨찾기 카드 `min-height: 155px` 고정, 모바일 2열 그리드 + 7번째 카드 중앙 정렬

**2. 버그 수정 2건**
- 체크박스 찌그러짐: `flex-shrink: 0; min-width: 16px` 추가, 16px 크기로 통일
- 마퀴 클리핑: `.card-name-text`를 `display: inline-block; max-width: 100%`로 변경, hover 시 `max-width: none; overflow: visible`로 전환 (부모가 clip)

**3. Gemini Google Search Grounding — 투자자 반응 섹션 추가**
- `/api/analysis` 응답에 `x_reaction` 필드 추가
- 국내 종목: Naver Finance 게시판 3-query 전략 (`site:finance.naver.com/item/board`, `site:cafe.naver.com 주식`, `{종목명} 주식 투자자 반응`) → 레이블 `📣 국내 투자자 반응`
- 해외 종목: `{symbol} site:x.com OR site:twitter.com` → 레이블 `📣 X 투자자 반응`
- 결과 없을 시 빈 문자열 `""` 반환 → 프론트 && 체크로 섹션 숨김
- 인용 번호 제거: `re.sub(r'\[\d+\]', '', text)`
- Grounding 실패 시 fallback: 일반 생성으로 전환 (try/except)
- 뉴스레터 (`_build_stock_digest`, `_build_digest_html`)에도 동일 로직 반영

**결정사항**
- 국내 종목에서 X/Twitter 검색이 공란인 이유: Google이 한국어 X 콘텐츠를 색인하지 않음 → Naver 기반으로 전환
- `x_reaction` 필드명 유지 (내부 키; 레이블은 프론트/메일에서 분기)

---

### 2026-06-03 - 법적 고지 대응, 랜딩 페이지

| 항목 | 내용 |
| --- | --- |
| 작업자 | Claude Sonnet 4.6 |
| 변경 파일 | `index.html`, `style.css`, `docs/ai-handoff.md`, `docs/ai-worklog.md` |
| 커밋 | `f1812e7`, `567c612` |

**1. 종목 가격 알림 기능 제거**
- 백엔드·프론트 코드에 실제로 구현되지 않았음을 확인 (문서에만 존재)
- 사용자 판단: 일반 증권앱과 차별점 없음 → 보류
- `docs/ai-handoff.md`, `docs/ai-worklog.md`에서 관련 항목 제거

**2. 회원가입 동의 체크박스 추가**
- 이유: 이메일 수집 + 뉴스레터 발송 서비스이므로 개인정보보호법·정보통신망법 최소 대응 필요
- 이용약관·개인정보 수집 동의 (필수) — 미체크 시 가입 버튼 비활성화
- 이메일 뉴스레터 수신 동의 (선택)
- 가입 완료 시 Firestore `users/{uid}`에 `consentAt`, `newsletterConsent` 저장
- 모달 열기/닫기/탭 전환 시 체크박스 초기화

**3. 랜딩 페이지 추가**
- 이유: 비로그인 첫 화면이 아이콘+한 줄 설명뿐으로 서비스 소개 부재
- 히어로 섹션: "AI 기반 주식 대시보드" 뱃지 + `MarketPulse` 그라디언트 타이틀 + 서브타이틀 + CTA 버튼 2개
- 기능 소개 카드 4개 (2열 그리드): 실시간 시세, 기술지표 차트, AI 투자의견, 이메일 다이제스트
- 모바일(600px 이하): 1열 전환, 타이틀 폰트 축소
- MarketOverview 티커 바는 히어로 위에 유지

---

### 2026-06-02 - 차트 기술지표, 52주 고저가, 투자의견 Gemini 경량화

| 항목 | 내용 |
| --- | --- |
| 작업자 | Claude Sonnet 4.6 |
| 변경 파일 | `main.py`, `index.html`, `docs/ai-handoff.md`, `docs/ai-worklog.md` |
| 커밋 | `2a6e7cc`, `377be60`, `a7a3b22` |

**1. 차트 기술 지표 추가**
- `main.py` `/api/chart` 응답에 `5. volume` 필드 추가 (yfinance `Volume`)
- `index.html` `ChartSection`에 지표 토글 버튼 구현 (MA5/MA20/MA60/BB/거래량)
- MA5(노랑), MA20(파랑), MA60(보라), 볼린저밴드 20일 2σ(회색 점선), 거래량 바(상승 초록/하락 빨강)
- 원격 충돌 해소: 리모트에 차트 AI투자의견·가격알림 기능이 추가되어 있었음 — 두 세트 모두 보존

**2. 52주 신고가/신저가 범위 바**
- `/api/quote`, `/api/quotes` 응답에 `12. 52w_high`, `13. 52w_low` 추가 (yfinance `year_high/year_low`)
- `Week52Bar` 컴포넌트 신규 작성 — 저가~현재가 채움 바 + 현재가 위치 도트
- 도트 색상: 고가 70% 이상 초록, 저가 30% 이하 빨강, 중간 회색
- `FavoriteCard`, `MobilePriceCard` 양쪽에 적용

**3. 차트 투자의견 Gemini 경량화**
- 문제: 종목 선택마다 `/api/analysis` 호출 → `_gemini_stock_analysis`가 투자의견 5문장 + 뉴스 기사별 4문장 요약 × 5개 생성 → 15~20초 소요
- 원인: 차트는 `comment`만 표시하는데 뉴스레터용 `news_items`까지 함께 생성
- 수정: `_gemini_chart_comment` 함수 분리 — 헤드라인만 참고해 2~3문장만 생성 → 3~5초로 단축
- `_gemini_stock_analysis`(뉴스 요약 포함)는 뉴스레터 발송 전용으로 유지

**결정사항**
- 종목 가격 알림 기능: 일반 증권앱과 차별점 없다는 판단 → 보류. cron-job.org job 설정도 불필요

---

### 2026-06-01 - Gemini 안정화, 수신해지, 관리자강제발송, 차트AI투자의견, 가격알림

| 항목 | 내용 |
| --- | --- |
| 작업자 | Claude Sonnet 4.6 |
| 변경 파일 | `main.py`, `index.html`, `docs/ai-handoff.md`, `docs/ai-worklog.md` |
| 커밋 | `0eed973`, `137a66c`, `571a30e`, `b5642c4`, `f54cd36`, `121d2d7`, `a5a3420`, `5fd2c27`, `1c45e58` |

**1. Gemini 503 재시도 강화**
- 기존 3회(30s+60s) → 5회 지수 백오프(30→60→120→120s)
- 반복되는 503 과부하 상황에서 빈 뉴스레터 발송 방지

**2. Gemini 모델 폴백 추가**
- `_gemini_stock_analysis`에 `model` 파라미터 추가
- 지정 모델 2회 실패 시 `gemini-2.0-flash`로 자동 전환
- 뉴스레터: `gemini-2.5-flash`(20회/일 한도) 유지
- 차트 투자의견: `gemini-2.0-flash`(1500회/일) 사용 — 할당량 분리
- **주의**: `gemini-1.5-flash`는 이 계정 v1beta에서 404 — 사용 불가

**3. 수신 해지 링크**
- `GET /api/unsubscribe?uid=&token=` 엔드포인트
- HMAC-SHA256(CRON_SECRET, uid) 토큰으로 인증 — 링크 위변조 불가
- 메일 하단 "수신 해지" 링크 삽입

**4. 관리자 강제 발송 버튼**
- `POST /api/admin/digest/force` (admin Bearer 토큰 인증)
- 관리자 패널 헤더에 "강제 발송" 버튼 추가
- `BackgroundTasks`로 즉시 응답 → Render 30초 타임아웃 방지

**5. 차트 AI 투자의견**
- `GET /api/analysis?symbol=&name=&is_korean=` 엔드포인트
- `gemini-2.0-flash` 사용, 30분 캐시
- 차트 하단 AI 투자의견 섹션 표시 (로딩/완료/오류 상태)
- AI 참고 의견 면책 문구 포함

**6. 도메인**
- `ahdoyoon.site` Firebase Hosting 커스텀 도메인 연결 완료

---

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
