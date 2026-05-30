# MarketPulse 배포 체크리스트

배포 완료 직후 아래 순서대로 점검한다.
AI가 배포할 때도 이 파일을 기준으로 항목을 체크하고, 결과를 `docs/ai-worklog.md`에 기록한다.

---

## 0. 사전 확인

- [ ] `git status` 깨끗한 상태 (미커밋 변경 없음)
- [ ] `docs/ai-handoff.md` 현재 상태 최신화 여부 확인

---

## 1. 자동 점검 (스크립트)

```bash
export CRON_SECRET=your_cron_secret
bash scripts/post-deploy.sh
```

통과 기준: **0 실패**
실패 시 원인 수정 → 재배포 후 재점검.

스크립트가 체크하는 항목:
- API 엔드포인트 5개 HTTP 200 응답
- 소스 코드 내 API 키 하드코딩 여부
- `.env` 파일 git 추적 여부
- Digest dry-run 정상 응답

---

## 2. UI 수동 점검

브라우저에서 https://portfolio-4ffcf.web.app 열고 확인.

**데스크탑 (1280px 이상)**
- [ ] 티커 바(시장 지수) 정상 표시
- [ ] 로그인 전 화면 정상 렌더링
- [ ] 로그인 후 즐겨찾기 카드 표시
- [ ] 차트 데이터 로드
- [ ] 뉴스 섹션 로드

**모바일 (브라우저 개발자도구 → 375px)**
- [ ] 헤더 아이콘 버튼 한 줄 배치 이상 없음
- [ ] 커스텀 셀렉트(바텀시트) 열림/닫힘 정상
- [ ] 현재가 카드 표시 이상 없음

---

## 3. 뉴스레터 발송 테스트

백엔드(`main.py`) 변경이 있을 때만 수행.

```bash
# dry-run — 메일 미발송, 응답만 확인
curl -s -X POST \
  -H "x-cron-secret: $CRON_SECRET" \
  "https://stockboard-fhh4.onrender.com/api/cron/digest?dry_run=true&include_details=true"
```

- [ ] `resend_configured: true`
- [ ] `eligible` 수가 예상과 일치
- [ ] Gemini 관련 변경이 있었다면 `?force=true` 로 실제 발송 후 메일 수신 확인

---

## 4. 보안 체크 (자동 점검 보완)

- [ ] Render 대시보드에서 환경변수 목록 이상 없는지 확인
  - `GEMINI_API_KEY`, `RESEND_API_KEY`, `CRON_SECRET`, `FIREBASE_SERVICE_ACCOUNT`, `MAIL_FROM`, `ADMIN_UIDS`
- [ ] `requirements.txt` 에 버전 미고정 패키지가 있다면 worklog에 메모
- [ ] 새로 추가한 엔드포인트에 인증 누락 없는지 확인

---

## 5. 완료 처리

- [ ] `docs/ai-worklog.md` 에 배포 내용 기록 (변경 파일, 목적, 점검 결과)
- [ ] `docs/ai-handoff.md` 현재 상태 갱신

---

## AI 에이전트 안내

- 배포(`firebase deploy` 또는 `git push`) 후 반드시 이 파일을 체크한다.
- 1번(스크립트)과 3번(curl) 항목은 직접 실행한다.
- 2번(UI)은 사용자에게 확인 요청한다.
- 4번 Render 대시보드 확인은 사용자에게 요청한다.
- 모든 결과를 worklog에 한 줄씩 기록한다.
