# Stockboard 프로젝트 기록

## 1. 프로젝트 개요

| 항목 | 내용 |
| --- | --- |
| 프로젝트명 | Stockboard / MarketPulse |
| 목적 | 관심 종목의 현재가, 차트, 관련 뉴스를 한 화면에서 확인하는 개인화 주식 대시보드 |
| 주요 사용자 | 로그인한 회원 |
| 현재 배포 | Frontend: Firebase Hosting, Backend: Render FastAPI |
| 프론트 URL | https://portfolio-4ffcf.web.app/ |
| 백엔드 API | https://stockboard-fhh4.onrender.com/api |
| 저장소 | https://github.com/dykim1230-hub/stockboard.git |

## 2. 핵심 기능

| 기능 | 상태 | 설명 |
| --- | --- | --- |
| 회원가입/로그인 | 완료 | Firebase Auth 기반 이메일 로그인 |
| 즐겨찾기 종목 저장 | 완료 | Firestore `users/{uid}` 문서에 `favorites` 저장 |
| 종목 검색 | 완료 | 국내 종목은 FinanceDataReader, 해외 종목은 Yahoo Finance 검색 사용 |
| 현재가 조회 | 완료 | `yfinance.fast_info` 기반 |
| 차트 조회 | 완료 | 최근 1년 가격 데이터를 Chart.js로 렌더링 |
| 관련 뉴스 | 완료 | Google News RSS 기반 |
| 프로필 관리 | 완료 | 비밀번호 변경, 회원 탈퇴 |
| 관리자 패널 | 완료 | 회원 목록 조회, 계정 삭제, 비밀번호 초기화 링크 생성 |
| 회원별 메일 요약 | 완료 | Resend + Render Cron Job, Gemini AI 투자의견·뉴스 요약 포함 |
| 문의 폼 | 완료 | 푸터 ContactModal, POST /api/contact, IP rate limit |
| 초대 랜딩 페이지 | 완료 | `/invite?ref=...` 접속 시 InviteLanding 렌더링, ref → sessionStorage 저장 |

## 3. 기술 스택

| 영역 | 사용 기술 |
| --- | --- |
| Frontend | HTML, CSS, React UMD, Babel in browser, Chart.js |
| Backend | Python, FastAPI, Uvicorn |
| Auth | Firebase Authentication |
| Database | Firebase Firestore |
| Hosting | Firebase Hosting |
| Backend Deploy | Render Web Service |
| Stock Data | yfinance, FinanceDataReader |
| News | Google News RSS |
| Email 예정 | Resend |
| Scheduler 예정 | Render Cron Job |

## 4. 현재 파일 구조

```text
stockboard/
├── index.html
├── style.css
├── app.jsx
├── main.py
├── requirements.txt
├── firebase.json
├── Procfile
├── test_news.py
└── docs/
    └── notion-project-log.md
```

## 5. 배포 구조

### Frontend

- Firebase Hosting 사용
- `firebase.json`에서 public 경로를 프로젝트 루트 `.`로 설정
- 모든 경로는 `index.html`로 rewrite
- 백엔드 API는 `BASE_URL = https://stockboard-fhh4.onrender.com/api`

### Backend

- Render Web Service 사용
- 실행 명령은 `Procfile` 기준

```text
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### 필요한 환경변수

| 환경변수 | 용도 |
| --- | --- |
| `FIREBASE_SERVICE_ACCOUNT` | Firebase Admin SDK 인증 |
| `ADMIN_UIDS` | 관리자 UID 목록, 콤마 구분 |
| `RESEND_API_KEY` | 메일 발송 API 키 |
| `MAIL_FROM` | 메일 발신자 주소 |
| `CRON_SECRET` | Render Cron Job 호출 인증 |
| `GEMINI_API_KEY` | Google Gemini AI 요약 API 키 |
| `CONTACT_ADMIN_EMAIL` | 문의 폼 수신 이메일 (없으면 MAIL_FROM 사용) |

## 6. 데이터 모델

### 현재 Firestore 사용자 문서

```js
users/{uid} {
  favorites: [
    {
      symbol: "005930.KS",
      name: "삼성전자",
      currency: "KRW",
      isKorean: true
    }
  ]
}
```

### 메일 요약 기능 추가 예정 모델

```js
users/{uid} {
  favorites: [...],
  emailDigest: {
    enabled: true,
    hour: 8,
    timezone: "Asia/Seoul",
    maxNewsPerStock: 5,
    lastSentDate: "2026-05-14",
    lastSentAt: "...",
    lastError: null
  }
}
```

## 7. 메일링 기능 설계

### 결정된 정책

| 항목 | 결정 |
| --- | --- |
| 수신 동의 | 기본 비활성화, 사용자가 직접 켜야 함 |
| 발송 시간 | 회원이 1시간 단위로 선택 |
| 발송 횟수 | 회원별 선택 시간에 하루 1회만 발송 |
| 발송 기준 시간대 | Asia/Seoul |
| 종목 대상 | 회원 즐겨찾기 전체, 최대 7개 |
| 뉴스 개수 | 종목당 5개 |
| 메일 서비스 | Resend 사용 예정 |
| 스케줄러 | Render Cron Job 사용 예정 |

### 발송 흐름

```text
1. Render Cron Job이 매시 정각 `/api/cron/digest` 호출
2. 현재 Asia/Seoul 기준 hour 계산
3. Firestore에서 emailDigest.enabled = true인 사용자 조회
4. emailDigest.hour가 현재 hour와 같은 사용자만 대상
5. lastSentDate가 오늘이면 skip
6. 사용자의 favorites 기준으로 시세/뉴스 요약 생성
7. Resend API로 이메일 발송
8. 성공 시 lastSentDate, lastSentAt 업데이트
9. 실패 시 lastError 기록
```

### 중복 발송 방지

```text
lastSentDate == 오늘 날짜이면 발송하지 않는다.
```

예시:

```text
사용자 선택 시간: 08시
오늘 날짜: 2026-05-14
lastSentDate: 2026-05-14
결과: 이미 오늘 발송했으므로 skip
```

## 8. Resend / 도메인 설정 기록

### 보유 도메인

```text
ahdoyoon.site
```

구매처:

```text
가비아
```

### 발신 주소 예정

```text
MarketPulse <no-reply@ahdoyoon.site>
```

### Resend DNS 설정

Resend에서 도메인을 추가한 뒤 표시되는 DNS 레코드를 가비아 DNS에 등록한다.

| 용도 | 타입 | 설명 |
| --- | --- | --- |
| DKIM | TXT | 도메인 서명 인증 |
| SPF | TXT | Resend가 도메인 대신 메일을 보낼 수 있음을 선언 |
| Bounce/Feedback | MX | 반송/피드백 처리를 위한 레코드 |
| DMARC | TXT | 선택 사항, 정책은 초기에는 `p=none` |

DMARC는 가비아에 별도 DMARC 메뉴가 없어도 TXT 레코드로 추가한다.

```text
Type: TXT
Host: _dmarc
Value: v=DMARC1; p=none;
```

## 9. 최근 작업 히스토리

| 날짜 | 커밋 | 내용 |
| --- | --- | --- |
| 2026-06-25 | `bddb336` | Gemini 503 fallback — `gemini-2.0-flash` 4번째 시도 모델 추가 (2.5-flash-lite × 2 → 2.5-flash → 2.0-flash) |
| 2026-06-25 | `419c5d9` | yfinance rate limit 수정 — 지수별 개별 캐시 + 재시도 3회(3s/6s) + max_workers 5→2 |
| 2026-06-21 | `3fc857f`, `5a75ae4` | Babel 버전 고정(@7.23.10), 캔들스틱 차트 복원(커스텀 afterDatasetsDraw 플러그인) |
| 2026-06-16 | — | 초대 랜딩 페이지(InviteLanding) 추가 — `/invite?ref=...` 전용, ref sessionStorage 저장, 샘플 뉴스레터 카드 3개 |
| 2026-06-11 | `3ea2c70` | 시장현황에 경제일정 통합(3초 슬라이드 롤링), 가격 차트 라인→캔들스틱 전환(`/api/chart` OHLC 추가) |
| 2026-06-11 | `4731b59`, `4efdacc` | 경제지표 캘린더 FOMC/BOK 파싱 버그 수정, BLS 호출 제외, cron-job.org 운영 개시 |
| 2026-06-08 | `e180f66` | 로그인 후 공백 화면 버그 수정 — ChartSection stale analysis JSX(ReferenceError) 제거, EcCalBoundary 추가, EconomicCalendar 재활성화 |
| 2026-06-08 | `8aebff1` | Gemini 2.5-flash-lite 고정, 뉴스요약 재시도 3회 추가, 종료된 폴백 모델 정리 |
| 2026-06-05 | `e394a30` | 웹 AI 의견 제거, 문의 폼 추가, Gemini 폴백 3단계 |
| 2026-06-03 | `47df745` | UI 개선 5종, 버그 수정, Gemini Search Grounding |
| 2026-06-01 | 다수 | 수신해지, 관리자강제발송, 차트AI투자의견, 도메인연결 |
| 2026-05-30 | `672c4ef` | Gemini JSON 파싱 오류 수정, 배포 자동 점검 체계 |
| 2026-05-26 | `b589375` | AI 뉴스요약 추가, 뉴스레터 구조 개편, rate limit 버그 수정 |
| 2026-05-19 | `eb19e29` | 성능 개선, 뉴스 정렬, 관리자 버그 수정 |
| 구버전 | `d39e6ae` | Yahoo Finance RSS를 Google News RSS로 교체 |
| `6835f71` | 사용자 프로필, 회원 탈퇴, 관리자 패널 추가 |
| `662cf93` | BASE_URL을 Render 배포 주소로 변경 |
| `2154b16` | Firebase Auth/Firestore 로그인, Render 배포 설정 추가 |
| `3bf4041` | 뉴스 미표시 버그 수정, 빈 결과 캐시 방지, RSS 재시도 추가 |
| `415620d` | TTL 캐시 추가 및 `fast_info` 전환 |
| `b1eed1a` | 뉴스/검색 버그 수정, Naver 403 대응, `is_korean` 플래그 오류 수정 |
| `fd0645e` | CORS 설정 수정 |

## 10. 이슈 및 주의사항

| 항목 | 내용 |
| --- | --- |
| 프론트 구조 | 현재 `index.html` 안에서 React/Babel을 직접 사용하므로 규모가 커지면 Vite 등으로 전환 검토 필요 |
| API 안정성 | yfinance, Google News RSS는 비공식/외부 의존성이 있어 실패 대비 필요 |
| 메일 발송 | 수신 동의, 수신 해지, 실패 로그, 중복 발송 방지 필요 |
| DNS | `portfolio-4ffcf.web.app`에는 SPF/DKIM 설정 불가, 소유 도메인 `ahdoyoon.site` 사용 |
| 보안 | Firebase Service Account, Resend API Key는 Render 환경변수로만 관리 |

## 11. 다음 작업

- [ ] **(최우선, 2026-06-11)** 문의 폼("관리자에게 메일 보내기") 메일 미수신 문제 — `/api/contact`는 `{"ok":true}` 반환(Resend API 호출 자체는 성공)하지만 실제 메일이 도착하지 않음. Resend 대시보드(Emails/Logs)에서 발송 기록·수신 주소·전달 상태 확인 필요, `CONTACT_ADMIN_EMAIL`/`MAIL_FROM` 값 점검
- [ ] Resend에서 `ahdoyoon.site` DNS 인증 완료
- [ ] Render 환경변수에 `RESEND_API_KEY`, `MAIL_FROM` 추가
- [x] 회원 설정 UI 추가
- [x] Firestore `emailDigest` 저장 로직 추가
- [x] 백엔드 메일 HTML 생성 함수 추가
- [x] Resend 발송 함수 추가
- [x] Render Cron Job용 엔드포인트 추가
- [x] 하루 1회 중복 발송 방지 로직 추가
- [ ] Render 환경변수에 `CRON_SECRET` 추가
- [ ] Render Cron Job 생성
- [ ] 테스트 계정으로 실제 메일 발송 검증
- [ ] 수신 해지/설정 변경 링크 추가

## 12. Notion 카테고리 추천

### 프로젝트 홈

- 프로젝트 개요
- 현재 URL
- 기술 스택
- 주요 기능
- 다음 작업

### 작업 로그

- 날짜
- 작업 내용
- 문제
- 해결
- 남은 일

### 기능 설계

- 회원 기능
- 즐겨찾기
- 뉴스/시세
- 메일 요약
- 관리자 기능

### 배포/인프라

- Firebase Hosting
- Render
- Firestore
- Resend
- DNS

### 트러블슈팅

- 증상
- 원인
- 해결 방법
- 관련 파일/커밋

### 의사결정 기록

- 결정일
- 결정 내용
- 선택지
- 선택 이유
- 나중에 재검토할 조건
