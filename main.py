# -*- coding: utf-8 -*-
from fastapi import FastAPI, Query, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import FinanceDataReader as fdr
import time
import xml.etree.ElementTree as ET
import os
import json
import urllib.parse
import html
from datetime import datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.utils import parsedate_to_datetime

# ── Firebase Admin ─────────────────────────────────────────
import firebase_admin
from firebase_admin import credentials, auth as admin_auth
from firebase_admin import firestore

_admin_initialized = False

def _init_firebase_admin():
    global _admin_initialized
    if _admin_initialized:
        return True
    sa_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
    if not sa_json:
        return False
    try:
        cred = credentials.Certificate(json.loads(sa_json))
        firebase_admin.initialize_app(cred)
        _admin_initialized = True
        return True
    except Exception as e:
        print(f"Firebase Admin init error: {e}")
        return False

ADMIN_UIDS = set(filter(None, os.environ.get("ADMIN_UIDS", "").split(",")))

def _verify_token(authorization: str) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization[7:]
    try:
        return admin_auth.verify_id_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

def _verify_admin(authorization: str) -> dict:
    decoded = _verify_token(authorization)
    if decoded["uid"] not in ADMIN_UIDS:
        raise HTTPException(status_code=403, detail="Forbidden")
    return decoded

def _get_firestore_client():
    if not _init_firebase_admin():
        raise HTTPException(status_code=503, detail="Firebase Admin SDK not configured")
    return firestore.client()

app = FastAPI(title="Stock Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── TTL 캐시 ───────────────────────────────────────────────
_cache: dict = {}

def _get_cache(key):
    if key in _cache:
        value, exp = _cache[key]
        if time.time() < exp:
            return value, True
    return None, False

def _set_cache(key, value, ttl: int):
    _cache[key] = (value, time.time() + ttl)

# ── KRX 데이터 (검색용) ────────────────────────────────────
krx_df = None
etf_df = None

def get_krx_data():
    global krx_df, etf_df
    if krx_df is None:
        try:
            krx_df = fdr.StockListing('KRX')
            etf_df = fdr.StockListing('ETF/KR')
        except Exception as e:
            print("Failed to load KRX/ETF data:", e)
    return krx_df, etf_df

def is_korean_symbol(symbol: str) -> bool:
    return symbol.endswith('.KS') or symbol.endswith('.KQ')

# ── 시장 지수 ─────────────────────────────────────────────
MARKET_INDICES = [
    {"symbol": "^GSPC",  "name": "S&P 500", "currency": "USD"},
    {"symbol": "^IXIC",  "name": "NASDAQ",  "currency": "USD"},
    {"symbol": "^KS11",  "name": "KOSPI",   "currency": "KRW"},
    {"symbol": "^KQ11",  "name": "KOSDAQ",  "currency": "KRW"},
    {"symbol": "KRW=X",  "name": "원/달러", "currency": "KRW"},
]

def _fetch_index(idx):
    fi = yf.Ticker(idx["symbol"]).fast_info
    price = fi.last_price
    prev = fi.previous_close
    if price is None:
        return None
    price = float(price)
    prev = float(prev or price)
    change = price - prev
    change_pct = (change / prev * 100) if prev else 0.0
    return {
        "symbol": idx["symbol"],
        "name": idx["name"],
        "price": price,
        "change": change,
        "change_pct": change_pct,
        "currency": idx["currency"],
    }

@app.get("/api/market")
def get_market():
    cache_key = "market:overview"
    cached, hit = _get_cache(cache_key)
    if hit:
        return cached

    result = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(_fetch_index, idx): idx for idx in MARKET_INDICES}
        for future in as_completed(futures):
            try:
                item = future.result()
                if item:
                    result.append(item)
            except Exception as e:
                print(f"Market index error {futures[future]['symbol']}: {e}")

    result.sort(key=lambda x: [i["symbol"] for i in MARKET_INDICES].index(x["symbol"]))
    if result:
        _set_cache(cache_key, result, ttl=300)
    return result


# ── 검색 ──────────────────────────────────────────────────
@app.get("/api/search")
def search_stock(q: str = Query(...)):
    if not q:
        return []

    cache_key = f"search:{q.lower()}"
    cached, hit = _get_cache(cache_key)
    if hit:
        return cached

    results = []
    added_symbols = set()

    df_krx, df_etf = get_krx_data()

    def search_df(df, is_etf=False):
        if df is None or df.empty:
            return
        code_col = 'Symbol' if is_etf else 'Code'
        name_col = 'Name'
        market_col = 'Market' if not is_etf else None
        if name_col in df.columns and code_col in df.columns:
            matches = df[
                df[name_col].str.contains(q, case=False, na=False) |
                df[code_col].str.contains(q, case=False, na=False)
            ]
            for _, row in matches.head(7).iterrows():
                code = str(row[code_col])
                if is_etf:
                    yf_symbol = f"{code}.KS"
                else:
                    market = str(row.get(market_col, ''))
                    yf_symbol = f"{code}.KQ" if 'KOSDAQ' in market else f"{code}.KS"
                if yf_symbol not in added_symbols:
                    results.append({
                        "1. symbol": yf_symbol,
                        "2. name": row[name_col],
                        "3. currency": "KRW",
                        "4. is_korean": True
                    })
                    added_symbols.add(yf_symbol)

    try:
        search_df(df_krx, is_etf=False)
        search_df(df_etf, is_etf=True)
    except Exception as e:
        print("FDR search error:", e)

    if len(results) < 7:
        try:
            url = "https://query2.finance.yahoo.com/v1/finance/search"
            params = {"q": q, "quotesCount": 7, "newsCount": 0}
            headers = {"User-Agent": "Mozilla/5.0"}
            res = requests.get(url, params=params, headers=headers, timeout=5)
            res.raise_for_status()
            for quote in res.json().get("quotes", []):
                symbol = quote.get("symbol")
                if symbol and symbol not in added_symbols:
                    shortname = quote.get("shortname") or quote.get("longname") or symbol
                    is_kr = is_korean_symbol(symbol)
                    results.append({
                        "1. symbol": symbol,
                        "2. name": shortname,
                        "3. currency": "KRW" if is_kr else "USD",
                        "4. is_korean": is_kr
                    })
                    added_symbols.add(symbol)
        except Exception as e:
            print(f"Yahoo Search API error: {e}")

    result = results[:10]
    _set_cache(cache_key, result, ttl=300)  # 5분 캐시
    return result


# ── 현재가 (단건 + 배치) ──────────────────────────────────
@app.get("/api/quotes")
def get_quotes(symbols: str = Query(...)):
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()][:10]

    def fetch_one(sym):
        cached, hit = _get_cache(f"quote:{sym}")
        if hit:
            return sym, cached
        try:
            fi = yf.Ticker(sym).fast_info
            price = fi.last_price
            prev = fi.previous_close
            if price is None:
                return sym, None
            prev = prev or price
            price = float(price)
            prev = float(prev)
            change = price - prev
            change_pct = (change / prev * 100) if prev else 0.0
            currency = fi.currency or ("KRW" if is_korean_symbol(sym) else "USD")
            result = {
                "05. price": price,
                "09. change": change,
                "10. change percent": change_pct,
                "11. currency": currency,
            }
            _set_cache(f"quote:{sym}", result, ttl=180)
            return sym, result
        except Exception as e:
            print(f"Quote batch error for {sym}: {e}")
            return sym, None

    results = {}
    with ThreadPoolExecutor(max_workers=len(symbol_list)) as executor:
        for sym, data in executor.map(fetch_one, symbol_list):
            results[sym] = data
    return results

@app.get("/api/quote")
def get_quote(symbol: str = Query(...)):
    cache_key = f"quote:{symbol}"
    cached, hit = _get_cache(cache_key)
    if hit:
        return cached

    try:
        fi = yf.Ticker(symbol).fast_info
        price = fi.last_price
        prev = fi.previous_close

        if price is None:
            return None

        prev = prev or price
        price = float(price)
        prev = float(prev)
        change = price - prev
        change_pct = (change / prev * 100) if prev else 0.0
        currency = fi.currency or ("KRW" if is_korean_symbol(symbol) else "USD")

        result = {
            "05. price": price,
            "09. change": change,
            "10. change percent": change_pct,
            "11. currency": currency
        }
        _set_cache(cache_key, result, ttl=180)
        return result
    except Exception as e:
        print(f"Quote API error for {symbol}: {e}")
        return None


# ── 차트 ──────────────────────────────────────────────────
@app.get("/api/chart")
def get_chart(symbol: str = Query(...)):
    cache_key = f"chart:{symbol}"
    cached, hit = _get_cache(cache_key)
    if hit:
        return cached

    try:
        hist = yf.Ticker(symbol).history(period="1y")
        if hist.empty:
            return None
        data = {
            index.strftime("%Y-%m-%d"): {"4. close": float(row["Close"])}
            for index, row in hist.iterrows()
        }
        _set_cache(cache_key, data, ttl=3600)
        return data
    except Exception as e:
        print(f"Chart API error for {symbol}: {e}")
        return None


# ── 뉴스 ──────────────────────────────────────────────────
@app.get("/api/news")
def get_news(
    stock_name: str = Query(...),
    symbol: str = Query(None),
    is_korean: bool = Query(True)
):
    if not symbol:
        return []

    cache_key = f"news:{symbol}"
    cached, hit = _get_cache(cache_key)
    if hit:
        return cached

    result = _google_news_rss(stock_name, is_korean)
    if result:
        _set_cache(cache_key, result, ttl=1800)
    return result


def _parse_pub_date(date_str: str) -> datetime:
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        return datetime.min.replace(tzinfo=ZoneInfo("UTC"))

def _google_news_rss(stock_name: str, is_korean: bool) -> list:
    if is_korean:
        query = urllib.parse.quote(stock_name)
        url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
    else:
        query = urllib.parse.quote(f"{stock_name} stock")
        url = f"https://news.google.com/rss/search?q={query}&hl=en&gl=US&ceid=US:en"

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    for attempt in range(2):
        try:
            res = requests.get(url, headers=headers, timeout=15)
            res.raise_for_status()
            root = ET.fromstring(res.content)
            articles = []
            for item in root.findall(".//item")[:10]:
                title = item.findtext("title", "").strip()
                link = item.findtext("link", "").strip()
                pub_date = item.findtext("pubDate", "").strip()
                source_el = item.find("source")
                source = source_el.text.strip() if source_el is not None else "Google News"
                if title and link:
                    articles.append({
                        "title": title,
                        "summary": "",
                        "url": link,
                        "source": source,
                        "time_published": pub_date
                    })
            if articles:
                articles.sort(key=lambda a: _parse_pub_date(a["time_published"]), reverse=True)
                return articles
        except Exception as e:
            print(f"Google News RSS error (attempt {attempt+1}) for '{stock_name}': {e}")
    return []


# ── Email Digest ───────────────────────────────────────────

def _format_digest_price(value, currency):
    if value is None:
        return "-"
    if currency == "KRW":
        return f"{round(value):,}원"
    return f"${float(value):,.2f}"

def _format_digest_change(value, pct, currency):
    if value is None:
        return "-"
    prefix = "+" if value > 0 else ""
    amount = _format_digest_price(abs(value), currency)
    if currency != "KRW" and value < 0:
        amount = amount.replace("$", "-$", 1)
    elif currency == "KRW" and value < 0:
        amount = f"-{amount}"
    else:
        amount = f"{prefix}{amount}"
    return f"{amount} ({prefix}{float(pct or 0):.2f}%)"

def _build_stock_digest(stock: dict) -> dict:
    symbol = stock.get("symbol") or stock.get("1. symbol")
    name = stock.get("name") or stock.get("2. name") or symbol
    is_korean = stock.get("isKorean", stock.get("4. is_korean", True)) is not False
    quote = get_quote(symbol) if symbol else None
    news = _google_news_rss(name, is_korean)[:5] if symbol else []
    return {
        "symbol": symbol,
        "name": name,
        "quote": quote,
        "news": news,
    }

def _build_digest_html(user_email: str, summaries: list, sent_at: datetime) -> str:
    rows = []
    for item in summaries:
        quote = item.get("quote") or {}
        currency = quote.get("11. currency") or "KRW"
        price = _format_digest_price(quote.get("05. price"), currency)
        change = _format_digest_change(quote.get("09. change"), quote.get("10. change percent"), currency)
        news_items = item.get("news") or []
        news_html = "".join(
            f'<li style="margin:6px 0;"><a href="{html.escape(n.get("url", ""))}" style="color:#2563eb;text-decoration:none;">'
            f'{html.escape(n.get("title", ""))}</a>'
            f'<span style="color:#6b7280;"> - {html.escape(n.get("source", "Google News"))}</span></li>'
            for n in news_items
        ) or '<li style="color:#6b7280;">관련 뉴스가 없습니다.</li>'
        rows.append(f"""
        <section style="padding:18px 0;border-bottom:1px solid #e5e7eb;">
          <h2 style="margin:0 0 8px;font-size:18px;color:#111827;">{html.escape(item.get("name") or "-")} <span style="color:#6b7280;font-size:13px;">{html.escape(item.get("symbol") or "")}</span></h2>
          <div style="font-size:14px;color:#111827;">현재가: <strong>{price}</strong></div>
          <div style="font-size:14px;color:#111827;margin-top:4px;">등락: <strong>{change}</strong></div>
          <h3 style="margin:14px 0 6px;font-size:14px;color:#374151;">뉴스</h3>
          <ol style="padding-left:20px;margin:0;font-size:13px;line-height:1.5;">{news_html}</ol>
        </section>
        """)
    body = "".join(rows) or '<p style="color:#6b7280;">즐겨찾기 종목이 없습니다.</p>'
    sent_label = sent_at.strftime("%Y-%m-%d %H:%M")
    return f"""<!doctype html>
<html>
  <body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,'Apple SD Gothic Neo',sans-serif;">
    <div style="max-width:680px;margin:0 auto;padding:24px;">
      <div style="background:#ffffff;border-radius:10px;padding:28px;">
        <h1 style="margin:0 0 6px;font-size:24px;color:#111827;">MarketPulse 일일 요약</h1>
        <p style="margin:0 0 14px;font-size:13px;color:#6b7280;">{html.escape(user_email)} · {sent_label} Asia/Seoul</p>
        <a href="https://portfolio-4ffcf.web.app"
           style="display:inline-block;background:#2563eb;color:#ffffff;text-decoration:none;padding:11px 26px;border-radius:8px;font-size:14px;font-weight:600;margin-bottom:20px;">
          대시보드 바로가기 →
        </a>
        {body}
        <div style="margin-top:24px;text-align:center;">
          <a href="https://portfolio-4ffcf.web.app"
             style="display:inline-block;background:#1e293b;color:#ffffff;text-decoration:none;padding:12px 32px;border-radius:8px;font-size:14px;font-weight:600;">
            📈 MarketPulse 열기
          </a>
        </div>
        <p style="margin:16px 0 0;font-size:12px;color:#6b7280;text-align:center;">메일 수신 설정은 MarketPulse 내 계정에서 변경할 수 있습니다.</p>
      </div>
    </div>
  </body>
</html>"""

def _send_resend_email(to_email: str, subject: str, body_html: str):
    api_key = os.environ.get("RESEND_API_KEY")
    mail_from = os.environ.get("MAIL_FROM")
    if not api_key or not mail_from:
        raise RuntimeError("RESEND_API_KEY and MAIL_FROM are required")
    res = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "from": mail_from,
            "to": [to_email],
            "subject": subject,
            "html": body_html,
        },
        timeout=20,
    )
    if res.status_code >= 400:
        raise RuntimeError(f"Resend error {res.status_code}: {res.text}")
    return res.json()

def _mask_email(email: str | None) -> str | None:
    if not email or "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        return f"{local[0]}***@{domain}"
    return f"{local[:2]}***@{domain}"

def _parse_digest_hour(value) -> int | None:
    try:
        hour = int(value)
    except (TypeError, ValueError):
        return None
    if 0 <= hour <= 23:
        return hour
    return None

def _run_digest_job(dry_run: bool = False, include_details: bool = False) -> dict:
    db = _get_firestore_client()
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    today = now.strftime("%Y-%m-%d")
    current_hour = now.hour
    stats = {
        "checked": 0,
        "eligible": 0,
        "sent": 0,
        "skipped": 0,
        "failed": 0,
        "dry_run": dry_run,
        "date": today,
        "current_hour": current_hour,
        "resend_configured": bool(os.environ.get("RESEND_API_KEY") and os.environ.get("MAIL_FROM")),
        "skip_reasons": {
            "disabled": 0,
            "invalid_hour": 0,
            "hour_mismatch": 0,
            "already_sent_today": 0,
            "missing_email": 0,
            "missing_favorites": 0,
        },
    }
    if include_details:
        stats["details"] = []

    for doc in db.collection("users").stream():
        stats["checked"] += 1
        data = doc.to_dict() or {}
        digest = data.get("emailDigest") or {}
        if not digest.get("enabled"):
            stats["skipped"] += 1
            stats["skip_reasons"]["disabled"] += 1
            continue
        digest_hour = _parse_digest_hour(digest.get("hour"))
        if digest_hour is None:
            stats["skipped"] += 1
            stats["skip_reasons"]["invalid_hour"] += 1
            if include_details:
                stats["details"].append({"uid": doc.id, "status": "skipped", "reason": "invalid_hour"})
            continue
        if digest_hour != current_hour:
            stats["skipped"] += 1
            stats["skip_reasons"]["hour_mismatch"] += 1
            if include_details:
                stats["details"].append({"uid": doc.id, "status": "skipped", "reason": "hour_mismatch", "configured_hour": digest_hour})
            continue
        if digest.get("lastSentDate") == today:
            stats["skipped"] += 1
            stats["skip_reasons"]["already_sent_today"] += 1
            if include_details:
                stats["details"].append({"uid": doc.id, "status": "skipped", "reason": "already_sent_today"})
            continue

        email = data.get("email")
        if not email:
            try:
                email = admin_auth.get_user(doc.id).email
            except Exception:
                email = None
        favorites = (data.get("favorites") or [])[:7]
        if not email:
            doc.reference.set({"emailDigest": {"lastError": "Missing email"}}, merge=True)
            stats["skip_reasons"]["missing_email"] += 1
            stats["failed"] += 1
            continue
        if not favorites:
            doc.reference.set({"emailDigest": {"lastError": "Missing favorites"}}, merge=True)
            stats["skip_reasons"]["missing_favorites"] += 1
            stats["failed"] += 1
            if include_details:
                stats["details"].append({"uid": doc.id, "email": _mask_email(email), "status": "failed", "reason": "missing_favorites"})
            continue

        stats["eligible"] += 1
        try:
            summaries = [_build_stock_digest(stock) for stock in favorites]
            body = _build_digest_html(email, summaries, now)
            if not dry_run:
                _send_resend_email(email, f"MarketPulse 일일 요약 - {today}", body)
                doc.reference.set({
                    "email": email,
                    "emailDigest": {
                        "lastSentDate": today,
                        "lastSentAt": firestore.SERVER_TIMESTAMP,
                        "lastError": None,
                    }
                }, merge=True)
                stats["sent"] += 1
            if include_details:
                stats["details"].append({
                    "uid": doc.id,
                    "email": _mask_email(email),
                    "status": "eligible" if dry_run else "sent",
                    "favorites_count": len(favorites),
                })
        except Exception as e:
            doc.reference.set({"emailDigest": {"lastError": str(e)}}, merge=True)
            stats["failed"] += 1
            if include_details:
                stats["details"].append({"uid": doc.id, "email": _mask_email(email), "status": "failed", "reason": str(e)})

    return stats

@app.post("/api/cron/digest")
def run_digest_cron(
    x_cron_secret: str = Header(None),
    dry_run: bool = Query(False),
    include_details: bool = Query(False),
):
    cron_secret = os.environ.get("CRON_SECRET")
    if not cron_secret:
        raise HTTPException(status_code=503, detail="CRON_SECRET is not configured")
    if x_cron_secret != cron_secret:
        raise HTTPException(status_code=403, detail="Forbidden")
    return _run_digest_job(dry_run=dry_run, include_details=include_details)


# ── Admin API ──────────────────────────────────────────────

@app.get("/api/admin/check")
def admin_check(authorization: str = Header(None)):
    if not _init_firebase_admin() or not authorization:
        return {"is_admin": False}
    try:
        decoded = _verify_token(authorization)
        return {"is_admin": decoded["uid"] in ADMIN_UIDS}
    except Exception:
        return {"is_admin": False}

@app.get("/api/admin/users")
def admin_list_users(authorization: str = Header(None)):
    if not _init_firebase_admin():
        raise HTTPException(status_code=503, detail="Admin SDK not configured")
    _verify_admin(authorization)
    users = []
    for u in admin_auth.list_users().iterate_all():
        users.append({
            "uid": u.uid,
            "email": u.email or "",
            "last_sign_in": u.user_metadata.last_sign_in_time,
            "created": u.user_metadata.creation_time,
        })
    users.sort(key=lambda x: x["last_sign_in"] or 0, reverse=True)
    return users

@app.delete("/api/admin/users/{uid}")
def admin_delete_user(uid: str, authorization: str = Header(None)):
    if not _init_firebase_admin():
        raise HTTPException(status_code=503, detail="Admin SDK not configured")
    _verify_admin(authorization)
    admin_auth.delete_user(uid)
    return {"success": True}

@app.post("/api/admin/users/{uid}/reset-password")
def admin_reset_password(uid: str, authorization: str = Header(None)):
    if not _init_firebase_admin():
        raise HTTPException(status_code=503, detail="Admin SDK not configured")
    _verify_admin(authorization)
    user = admin_auth.get_user(uid)
    if not user.email:
        raise HTTPException(status_code=400, detail="No email")
    link = admin_auth.generate_password_reset_link(user.email)
    return {"success": True, "email": user.email, "reset_link": link}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
