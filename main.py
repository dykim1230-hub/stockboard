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

# ── Firebase Admin ─────────────────────────────────────────
import firebase_admin
from firebase_admin import credentials, auth as admin_auth

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


# ── 현재가 ────────────────────────────────────────────────
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

    result = _yahoo_rss_news(symbol)
    if result:  # 빈 결과는 캐시하지 않음 (일시적 오류로 인한 공백 방지)
        _set_cache(cache_key, result, ttl=1800)
    return result


def _yahoo_rss_news(symbol: str) -> list:
    rss_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    for attempt in range(2):  # 실패 시 1회 재시도
        try:
            res = requests.get(rss_url, headers=headers, timeout=15)
            res.raise_for_status()
            root = ET.fromstring(res.content)
            articles = []
            for item in root.findall(".//item")[:10]:
                title = item.findtext("title", "").strip()
                url = item.findtext("link", "").strip()
                summary = item.findtext("description", "").strip()
                pub_date = item.findtext("pubDate", "").strip()
                source_el = item.find("source")
                source = source_el.text.strip() if source_el is not None else "Yahoo Finance"
                if summary:
                    summary = BeautifulSoup(summary, "html.parser").get_text(strip=True)
                if title and url:
                    articles.append({
                        "title": title,
                        "summary": summary[:120] + ("..." if len(summary) > 120 else ""),
                        "url": url,
                        "source": source,
                        "time_published": pub_date
                    })
            if articles:
                return articles
        except Exception as e:
            print(f"Yahoo RSS news error (attempt {attempt+1}) for '{symbol}': {e}")
    return []


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
