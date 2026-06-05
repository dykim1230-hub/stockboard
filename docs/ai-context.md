# Stockboard AI Context

이 문서는 Claude, GPT, Codex 등 AI 도구가 Stockboard 프로젝트를 이어서 작업할 때 먼저 읽는 공용 컨텍스트입니다.

## 읽는 순서

1. `docs/ai-context.md`
2. `docs/ai-handoff.md`
3. `docs/ai-worklog.md`
4. 필요한 경우 `docs/notion-project-log.md`, `docs/email-digest-setup.md`

## 프로젝트 개요

| 항목 | 내용 |
| --- | --- |
| 프로젝트명 | Stockboard / MarketPulse |
| 목적 | 관심 종목의 현재가, 차트, 관련 뉴스를 한 화면에서 확인하는 개인화 주식 대시보드 |
| 주요 사용자 | Firebase Auth로 로그인한 사용자 |
| Frontend | Firebase Hosting |
| Backend | Render FastAPI |
| 프론트 URL | https://portfolio-4ffcf.web.app/ |
| 백엔드 API | https://stockboard-fhh4.onrender.com/api |
| 저장소 | https://github.com/dykim1230-hub/stockboard.git |

## 기술 스택

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
| Email | Resend |
| Scheduler | Render Cron Job |

## 주요 파일

| 파일 | 역할 |
| --- | --- |
| `index.html` | Firebase 초기화, React 앱 로딩, API BASE_URL 설정 |
| `app.jsx` | 프론트엔드 React 컴포넌트와 사용자 흐름 |
| `style.css` | 화면 스타일 |
| `main.py` | FastAPI 백엔드, 주식 검색/시세/뉴스/메일 다이제스트 API |
| `requirements.txt` | Python 의존성 |
| `Procfile` | Render 백엔드 실행 명령 |
| `firebase.json` | Firebase Hosting 설정 |
| `test_news.py` | 뉴스 API 테스트 |
| `test_digest_cron.py` | 메일 다이제스트 cron 테스트 |
| `docs/notion-project-log.md` | 프로젝트 전체 기록 |
| `docs/email-digest-setup.md` | 메일 다이제스트 설정 문서 |

## 배포 구조

Frontend는 Firebase Hosting을 사용하며 `firebase.json`의 public 경로는 프로젝트 루트 `.`입니다.

Backend는 Render Web Service에서 실행됩니다.

```text
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

프론트엔드의 API 주소는 `index.html` 안의 `BASE_URL` 값을 따릅니다.

```js
const BASE_URL = 'https://stockboard-fhh4.onrender.com/api';
```

## 주요 환경변수

| 환경변수 | 용도 |
| --- | --- |
| `FIREBASE_SERVICE_ACCOUNT` | Firebase Admin SDK 인증 |
| `ADMIN_UIDS` | 관리자 UID 목록, 콤마 구분 |
| `RESEND_API_KEY` | Resend 메일 발송 API 키 |
| `MAIL_FROM` | 메일 발신자 주소 |
| `CRON_SECRET` | Render Cron Job 호출 인증 |
| `GEMINI_API_KEY` | Google Gemini AI 요약 API 키 |
| `CONTACT_ADMIN_EMAIL` | 문의 폼 수신 이메일 (없으면 MAIL_FROM 사용) |

## 데이터 모델

Firestore 사용자 문서는 `users/{uid}` 형태입니다.

```js
{
  favorites: [
    {
      symbol: "005930.KS",
      name: "삼성전자",
      currency: "KRW",
      isKorean: true
    }
  ],
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

## 작업 원칙

- 작업 전 `docs/ai-handoff.md`를 읽고 현재 이어받을 일을 확인한다.
- 작업 중 구조적 결정이 생기면 `docs/ai-worklog.md`에 남긴다.
- 작업 종료 시 `docs/ai-handoff.md`의 현재 상태, 다음 작업, 주의사항을 갱신한다.
- 비밀값은 코드나 문서에 직접 적지 않는다. 환경변수 이름만 기록한다.
- 기존 배포 URL, Firebase 프로젝트, Render 서비스명을 바꾸기 전에는 사용자 확인을 받는다.
- 외부 API 의존성인 yfinance, FinanceDataReader, Google News RSS는 실패 가능성을 고려한다.
- 프론트는 현재 Vite/빌드 도구 없이 React UMD와 Babel in browser를 사용한다. 구조 전환은 별도 결정으로 다룬다.

## 현재 주의사항

- `index.html`과 `app.jsx`에 프론트 로직이 나뉘어 있을 수 있으므로 중복 구현 여부를 확인한다.
- Firebase client config는 공개 가능한 값이지만, Firebase Admin service account는 반드시 환경변수로만 관리한다.
- 메일 다이제스트는 중복 발송 방지를 위해 `emailDigest.lastSentDate`를 사용한다.
- Render Cron Job은 `x-cron-secret` 헤더로 보호한다.
