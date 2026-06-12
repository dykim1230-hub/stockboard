# Stockboard AI Handoff

이 문서는 다음 AI 도구가 바로 이어서 작업할 수 있도록 현재 상태와 다음 작업만 짧게 정리하는 인수인계 문서입니다.

## 현재 상태

| 항목 | 상태 |
| --- | --- |
| 기본 대시보드 | 구현됨 |
| Firebase Auth 로그인 | 구현됨 |
| Firestore 즐겨찾기 저장 | 구현됨 |
| 종목 검색/시세/차트 | 구현됨 |
| Google News RSS 뉴스 | 구현됨 (최신순 정렬 적용) |
| 관리자 패널 | 구현됨 (회원 목록 버그 수정 완료) |
| 회원별 메일 다이제스트 | 구현됨, 실제 발송 확인됨 |
| 메일 내 사이트 링크 버튼 | 구현됨 (2026-05-16) |
| Cron 진단 응답 | 구현됨 |
| 모바일 UI 개선 | 2차 완료 (2026-05-16) |
| 모바일 커스텀 셀렉트 | 구현됨 — 바텀시트 방식, 사파리 호환 |
| 모바일 헤더 아이콘 버튼 | 구현됨 — 원형 40px, 한 줄 배치 |
| 시장 현황 (MarketOverview) | 구현됨 (2026-05-16) — 로그인 전 누구나 확인 가능 |
| 데스크탑 2컬럼 레이아웃 | 구현됨 (2026-05-16) — 1024px 이상에서 차트+뉴스 나란히 |
| 마켓 티커 바 | 구현됨 (2026-05-16) — Bloomberg 스타일 얇은 가로 바 |
| 초기 로딩 성능 개선 | 완료 (2026-05-19) — React 프로덕션 빌드, 배치 quote API, /api/market 병렬화 |
| Render cold start 방지 | 완료 (2026-05-19) — cron-job.org keepalive job 추가 |
| 뉴스레터 AI 요약 | 완료 (2026-05-26) — 종목별 투자 의견 5문장 + 기사별 뉴스 4문장 요약, Gemini 2.5 Flash |
| 뉴스레터 구조 개편 | 완료 (2026-05-26) — 종목명 옆 가격, 투자 의견/뉴스 요약 소제목 구분 |
| 강제 발송 기능 | 완료 (2026-05-26) — /api/cron/digest?force=true 파라미터 추가 |
| 수신자별 뉴스레터 내용 불일치 버그 수정 | 완료 (2026-05-26) — Gemini rate limit으로 인한 내용 누락 수정 |
| Gemini JSON 파싱 오류 수정 | 완료 (2026-05-30) — greedy 정규식 → raw_decode 교체, Extra data 에러 방지 |
| 배포 자동 점검 체계 | 완료 (2026-05-30) — scripts/post-deploy.sh, docs/deploy-checklist.md 추가 |
| Gemini 503 재시도 강화 | 완료 (2026-06-01) — 3회→5회, 지수 백오프(30→60→120→120s) |
| Gemini 모델 폴백 | 완료 (2026-06-01) — 2.5-flash 실패 시 2.0-flash 자동 전환 |
| 수신 해지 링크 | 완료 (2026-06-01) — GET /api/unsubscribe, HMAC-SHA256 토큰 인증, 메일 하단 삽입 |
| 관리자 강제 발송 버튼 | 완료 (2026-06-01) — 관리자 패널 내 버튼, BackgroundTasks로 타임아웃 방지 |
| 차트 AI 투자의견 | 완료 (2026-06-01) — GET /api/analysis, gemini-2.0-flash, 30분 캐시, 차트 하단 표시 |
| ahdoyoon.site 도메인 연결 | 완료 (2026-06-01) — Firebase Hosting 커스텀 도메인 연결 |
| 차트 기술 지표 | 완료 (2026-06-02) — MA5/MA20/MA60, 볼린저밴드(20일 2σ), 거래량 바. 지표 토글 버튼 UI |
| 52주 신고가/신저가 바 | 완료 (2026-06-02) — 종목 카드 하단 범위 바, 현재가 위치 색상(초록/빨강/회색) |
| 차트 투자의견 Gemini 경량화 | 완료 (2026-06-02) — 종목 선택 시 뉴스 요약 불필요하게 생성하던 문제 수정. _gemini_chart_comment 분리, 2~3문장만 생성 |
| 회원가입 동의 체크박스 | 완료 (2026-06-03) — 이용약관·개인정보 수집 동의(필수), 뉴스레터 수신 동의(선택). consentAt/newsletterConsent Firestore 저장 |
| 랜딩 페이지 | 완료 (2026-06-03) — 비로그인 첫 화면. 히어로(타이틀/서브타이틀/CTA) + 기능 소개 카드 4개 |
| UI 개선 5종 | 완료 (2026-06-03) — 페이지 타이틀, 즐겨찾기 온보딩 패널, AI의견 위치 이동, 지표 툴팁, 카드 고정높이+모바일 2열 |
| 버그 수정 (체크박스/마퀴) | 완료 (2026-06-03) — 체크박스 flex-shrink 추가, 마퀴 inline-block 전환으로 클리핑 수정 |
| Gemini Google Search Grounding | 완료 (2026-06-03) — 투자자 반응 섹션. 국내: Naver 3-query, 해외: X/Twitter. x_reaction 필드 |
| 웹 AI 투자의견·뉴스요약 제거 | 완료 (2026-06-05) — Gemini 쿼터 절약 목적. `/api/analysis`, `_gemini_chart_comment` 삭제 |
| 문의 폼 (푸터) | 완료 (2026-06-05) — `POST /api/contact`, IP당 10분 3회 rate limit, ContactModal + Footer |
| Gemini 폴백 3단계 | 완료 (2026-06-05) — 2.5-flash → 2.0-flash → 1.5-flash. 쿼터소진 즉시전환, retryDelay 파싱 |
| Gemini 2.5-flash-lite 고정 + 뉴스요약 재시도 | 완료 (2026-06-08) — 종료된 1.5/2.0-flash 폴백 제거, 2.5-flash-lite 고정, _gemini_summarize 3회 재시도 추가 |
| 로그인 후 공백 화면 버그 수정 | 완료 (2026-06-08) — ChartSection stale analysis JSX 제거(ReferenceError 근본 원인), EcCalBoundary Error Boundary 추가, EconomicCalendar 재활성화 |
| Google 소셜 로그인 | 완료 (2026-06-12) — signInWithPopup, 신규 가입 시 Firestore users 문서 생성. Firebase Console Authorized domains에 ahdoyoon.site 추가 필요(완료) |
| 경제지표 캘린더 | 구현됨 (2026-06-08) + 버그수정 (2026-06-11) — `/api/cron/update-calendar`, `/api/economic-calendar`, FOMC/BOK 파싱 버그 수정 후 배포·cron-job.org 등록·실행 검증 완료(FOMC 2건, BOK_RATE 1건 정상 수집). BLS(미국 CPI/PPI/Employment)는 www.bls.gov Akamai 차단(403)으로 수집 함수 호출에서 제외, 보류 |
| 시장현황 내 경제일정 | 완료 (2026-06-11) — 별도 패널이던 "이번 주 경제 일정"을 시장현황(MarketOverview) 하단에 통합, 일정 여러 개일 때 3초 간격 위로 슬라이드 롤링 표시 (`market-econ-roll`) |
| 가격 차트 캔들스틱 전환 | 완료 (2026-06-11) — `/api/chart`에 OHLC 추가, `chartjs-chart-financial`로 라인 차트 → 캔들스틱 전환, MA/볼린저는 라인 오버레이 유지 |

## 다음 작업 후보

1. **문의 폼("관리자에게 메일 보내기") 미수신 문제 (진행 중)**
   - `/api/contact`는 `{"ok":true}`(200) 반환, `_send_resend_email`도 정상 — Resend API 호출 자체는 성공
   - 그런데 실제 수신 메일함에 도착하지 않음 (사용자 보고: "전송완료로 뜨는데 실제 메일은 오지 않는다")
   - 다음 단계: Resend 대시보드(resend.com → Emails/Logs)에서 실제 발송 기록·수신 주소·전달 상태 확인 필요. `CONTACT_ADMIN_EMAIL`/`MAIL_FROM` 값이 올바른 수신함을 가리키는지도 확인

2. **(선택) BLS 경제지표(CPI/PPI/Employment) 재추가**
   - `fetch_bls_calendar()` 함수는 보존되어 있으나 `/api/cron/update-calendar`에서 호출하지 않음
   - FRED(세인트루이스 연은) Release Dates API로 교체 검토: CPI(release_id=10), PPI(46), Employment Situation(50). `FRED_API_KEY` 환경변수 필요(무료 발급)

3. **PWA 전환**
   - `manifest.json` + `service-worker.js` 추가

> 포트폴리오 수익률 트래킹 — 기존 증권앱 대비 차별점 없음으로 폐기 결정 (2026-06-08)

> 종목 가격 알림 기능 — 일반 증권앱과 차별점 없음으로 보류 결정 (2026-06-02)

## 작업 시작 체크리스트

- [ ] `docs/ai-context.md`를 읽었다.
- [ ] 이 파일의 `현재 상태`와 `다음 작업 후보`를 확인했다.
- [ ] `git status --short`로 사용자 변경사항을 확인했다.
- [ ] 필요한 파일만 좁게 읽고 수정 범위를 정했다.

## 작업 종료 체크리스트

- [ ] 변경한 파일을 요약했다.
- [ ] **배포 후 `docs/deploy-checklist.md`를 따라 점검했다.**
- [ ] 다음 작업자가 이어받을 내용을 이 파일에 갱신했다.
- [ ] 중요한 결정사항은 `docs/ai-worklog.md`에 추가했다.

## 배포 후 점검 방법

```bash
export CRON_SECRET=your_secret
bash scripts/post-deploy.sh
```

자동 점검 후 `docs/deploy-checklist.md`의 수동 항목(UI, 메일)을 이어서 확인한다.

## 주의사항

- 사용자가 만들었거나 다른 AI가 만든 변경사항을 임의로 되돌리지 않는다.
- 배포 설정, Firebase 프로젝트, Render 서비스, 도메인 설정 변경은 사용자 확인 후 진행한다.
- API 키, service account JSON, cron secret 값은 문서에 직접 기록하지 않는다.
- 현재 프로젝트는 간단한 정적 프론트 구조다. Vite 등으로 전환하는 작업은 별도 범위로 잡는다.

## 마지막 인수인계

| 항목 | 내용 |
| --- | --- |
| 날짜 | 2026-06-12 |
| 작성자 | Claude Sonnet 4.6 |
| 작업 환경 | Windows 11. 백엔드는 push → Render 자동배포. 프론트는 firebase deploy --only hosting. |
| 내용 | Google 소셜 로그인 추가 — AuthModal에 signInWithPopup 적용, 신규 가입 시 Firestore users/{uid} 문서 생성(consentAt/newsletterConsent), 에러 코드별 메시지 분기. Firebase Console Authorized domains에 ahdoyoon.site 추가 완료. |
| 다음 우선순위 | 문의 폼 메일 미수신 문제(Resend 대시보드 확인 필요), 경제지표 캘린더 구현, PWA 전환 |
| Gemini 모델 현황 | 뉴스레터: 2.5-flash-lite(기본) → 2.5-flash(폴백). Grounding: google_search tool |
| 주의 | gemini-1.5-flash, gemini-2.0-flash 서비스 종료 확인(2026년 상반기) — 폴백 목록에서 완전 제거. EconomicCalendar는 현재 FOMC(2026-06-17, 07-29), BOK_RATE(2026-07-16) 데이터로 정상 표시됨. cron-job.org 잡: 매주 월요일 00:00 UTC `POST /api/cron/update-calendar`. 캔들스틱 차트는 `chartjs-chart-financial`(CDN) 의존 — 차트 라이브러리 변경 시 영향받음. Google 소셜 로그인 Authorized domains: ahdoyoon.site, portfolio-4ffcf.web.app 등록 완료. |
