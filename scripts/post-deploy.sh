#!/usr/bin/env bash
# MarketPulse 배포 후 자동 점검 스크립트
# 사용법: CRON_SECRET=your_secret bash scripts/post-deploy.sh
# API_URL 환경변수로 엔드포인트 덮어쓰기 가능 (기본값: Render URL)

BASE_URL="${API_URL:-https://stockboard-fhh4.onrender.com}"
CRON_SECRET="${CRON_SECRET:-}"
PASS=0
FAIL=0

green() { printf "\033[32m  v %s\033[0m\n" "$1"; PASS=$((PASS + 1)); }
red()   { printf "\033[31m  x %s\033[0m\n" "$1"; FAIL=$((FAIL + 1)); }
warn()  { printf "\033[33m  ! %s\033[0m\n" "$1"; }

check_http() {
  local name="$1" url="$2" method="${3:-GET}" extra="${4:-}"
  local status
  status=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" $extra "$url" --max-time 30 2>/dev/null)
  if [ "$status" = "200" ]; then
    green "$name"
  else
    red "$name (HTTP $status)"
  fi
}

echo ""
echo "=== MarketPulse 배포 후 점검 ==="
echo "  BASE_URL: $BASE_URL"
echo ""

# ── 1. API 엔드포인트 ──────────────────────────────────────
echo "[1/3] API 엔드포인트"
check_http "시장 현황  /api/market"  "$BASE_URL/api/market"
check_http "종목 검색  /api/search"  "$BASE_URL/api/search?q=AAPL"
check_http "현재가     /api/quote"   "$BASE_URL/api/quote?symbol=AAPL"
check_http "차트       /api/chart"   "$BASE_URL/api/chart?symbol=AAPL"
check_http "뉴스       /api/news"    "$BASE_URL/api/news?stock_name=Apple&symbol=AAPL&is_korean=false"

# ── 2. 보안 점검 ──────────────────────────────────────────
echo ""
echo "[2/3] 보안"

# 서버 시크릿 키 패턴 감지 (.py 파일만 — Firebase 공개키 등 오탐 방지)
if git ls-files "*.py" | xargs grep -lE "(sk-[A-Za-z0-9]{40,}|re_[A-Za-z0-9]{32,})" 2>/dev/null | grep -q .; then
  red "Python 소스에 서버 시크릿 키 패턴 감지 — 확인 필요"
else
  green "Python 소스 키 하드코딩 없음"
fi

# .env가 git에 추적되는지 확인
if git ls-files --error-unmatch .env 2>/dev/null; then
  red ".env 파일이 git에 추적되고 있음"
else
  green ".env 파일 git 미추적 (정상)"
fi

# ── 3. Digest Dry-Run ─────────────────────────────────────
echo ""
echo "[3/3] Digest Dry-Run"

if [ -z "$CRON_SECRET" ]; then
  warn "CRON_SECRET 미설정 — 건너뜀"
  warn "  export CRON_SECRET=your_secret 후 재실행"
else
  response=$(curl -s -X POST \
    -H "x-cron-secret: $CRON_SECRET" \
    "$BASE_URL/api/cron/digest?dry_run=true&include_details=true" \
    --max-time 120 2>/dev/null)

  if echo "$response" | grep -q '"eligible"'; then
    green "Digest dry-run 정상"
    checked=$(echo "$response" | grep -o '"checked":[0-9]*' | grep -o '[0-9]*')
    eligible=$(echo "$response" | grep -o '"eligible":[0-9]*' | grep -o '[0-9]*')
    resend=$(echo "$response" | grep -o '"resend_configured":[a-z]*' | grep -o '[a-z]*$')
    echo "     checked=$checked  eligible=$eligible  resend_configured=$resend"
  else
    red "Digest dry-run 실패"
    echo "     응답: ${response:0:300}"
  fi
fi

# ── 결과 ──────────────────────────────────────────────────
echo ""
echo "=== 결과: ${PASS} 통과 / ${FAIL} 실패 ==="
echo ""

if [ "$FAIL" -gt 0 ]; then
  echo "  실패 항목을 확인하세요. (docs/deploy-checklist.md 참고)"
  exit 1
else
  echo "  자동 점검 완료."
  echo "  docs/deploy-checklist.md 의 수동 항목(UI, 메일)을 이어서 확인하세요."
  exit 0
fi
