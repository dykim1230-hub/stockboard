# -*- coding: utf-8 -*-
from fastapi import FastAPI, Query, Header, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
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
import re
import hmac
import hashlib
from google import genai as google_genai

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


# ── Headline News & Gemini Summary ────────────────────────

def _fetch_headline_news(limit: int = 5) -> list:
    RSS_SOURCES = [
        # 언론사명, URL, 최대 수집 수
        ("매일경제", "https://www.mk.co.kr/rss/30100041/", 10),
        ("Google뉴스", "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtdHZHZ0pMVWlnQVAB?hl=ko&gl=KR&ceid=KR:ko", 20),
    ]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    candidates = []

    for source_name, url, fetch_limit in RSS_SOURCES:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.raise_for_status()
            root = ET.fromstring(res.content)
            for item in root.findall(".//item")[:fetch_limit]:
                title = re.sub(r"<[^>]+>", "", item.findtext("title", "")).strip()
                desc  = re.sub(r"<[^>]+>", "", item.findtext("description", "")).strip()
                link  = item.findtext("link", "").strip()
                pub   = item.findtext("pubDate", "").strip()
                # Google News RSS는 source 태그에 언론사명이 있음
                source_el = item.find("source")
                source = source_el.text.strip() if source_el is not None else source_name
                # description이 제목과 동일한 경우(Google News 패턴) 비움
                if desc and title and desc.startswith(title):
                    desc = ""
                if title:
                    candidates.append({
                        "title": title, "desc": desc,
                        "link": link, "pub": pub, "source": source,
                    })
        except Exception as e:
            print(f"Headline news fetch error ({source_name}): {e}")

    # 소스별 최대 2개 제한 + 제목 앞 20자 기준 중복 제거
    seen_titles, source_count, unique = set(), {}, []
    for n in candidates:
        title_key = n["title"][:20]
        src = n.get("source", "")
        if title_key in seen_titles:
            continue
        if source_count.get(src, 0) >= 2:
            continue
        seen_titles.add(title_key)
        source_count[src] = source_count.get(src, 0) + 1
        unique.append(n)
        if len(unique) >= limit:
            break

    return unique


def _extract_gemini_text(response) -> str:
    """gemini-2.5-flash thinking 모델은 response.text가 ValueError를 던질 수 있음.
    thinking part를 제외한 text part만 직접 추출한다."""
    try:
        return response.text or ""
    except (ValueError, AttributeError):
        pass
    try:
        parts = response.candidates[0].content.parts
        return "".join(
            p.text for p in parts
            if hasattr(p, "text") and not getattr(p, "thought", False)
        )
    except Exception:
        return ""


def _parse_first_json_array(text: str):
    """텍스트에서 첫 번째 완전한 JSON 배열만 파싱한다.
    응답 뒤에 설명 텍스트가 붙어도 Extra data 에러 없이 배열만 반환한다."""
    idx = text.find('[')
    if idx == -1:
        return None
    try:
        result, _ = json.JSONDecoder().raw_decode(text, idx)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass
    return None


def _gemini_summarize(news_items: list) -> list:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or not news_items:
        return []
    try:
        client = google_genai.Client(api_key=api_key)
        articles_text = "\n\n".join(
            f"{i+1}. 제목: {n['title']}"
            + (f"\n   내용: {n['desc']}" if n.get('desc') else "")
            + (f"\n   출처: {n['source']}" if n.get('source') else "")
            for i, n in enumerate(news_items)
        )
        prompt = (
            "아래 한국 경제 뉴스 기사들을 각각 3~4문장으로 요약해주세요.\n"
            "내용이 없는 기사는 제목과 배경 지식을 바탕으로 핵심을 유추해서 써주세요.\n"
            "독자가 오늘의 주요 경제 동향을 빠르게 파악할 수 있도록 구체적으로 써주세요.\n"
            "형식: 반드시 JSON 배열로만 응답하세요. 다른 텍스트 없이.\n"
            '예시: ["요약1", "요약2", "요약3", "요약4", "요약5"]\n\n'
            f"기사 목록:\n{articles_text}"
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        text = _extract_gemini_text(response).strip()
        summaries = _parse_first_json_array(text)
        if summaries is not None:
            return summaries[:len(news_items)]
        print(f"Gemini summarize: no JSON array found. text[:200]={text[:200]}")
    except Exception as e:
        print(f"Gemini summarize error: {e}")
    return []


def _gemini_stock_analysis(stock_summaries: list) -> list:
    """종목별 투자 의견(1줄) + 기사별 개별 요약(2문장) 한 번에 생성.
    반환: [{"comment": "...", "news_items": ["요약1", "요약2", ...]}, ...]
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    empty = [{"comment": "", "news_items": []} for _ in stock_summaries]
    if not api_key or not stock_summaries:
        return empty

    client = google_genai.Client(api_key=api_key)
    stocks_text = ""
    for i, item in enumerate(stock_summaries):
        quote = item.get("quote") or {}
        change_pct = quote.get("10. change percent", "0")
        news_list = "\n".join(
            f"   {j+1}) {n.get('title', '')}"
            for j, n in enumerate((item.get("news") or [])[:5])
        ) or "   1) 관련 뉴스 없음"
        stocks_text += (
            f"{i+1}. {item.get('name')} ({item.get('symbol')})\n"
            f"   등락: {change_pct}\n"
            f"   기사 목록:\n{news_list}\n\n"
        )
    prompt = (
        f"아래 {len(stock_summaries)}개 종목 각각에 대해 두 가지를 작성해주세요.\n"
        "1. comment: 등락률과 뉴스를 종합해 투자자 관점에서 오늘의 상황을 분석하고 포인트·주의사항을 5문장으로 작성\n"
        "2. news_items: 각 기사를 4문장으로 개별 요약한 배열 (기사 순서 그대로, 핵심 내용과 배경을 구체적으로)\n\n"
        "형식: 반드시 JSON 배열로만 응답하세요. 다른 텍스트 없이.\n"
        '예시: [{"comment": "...", "news_items": ["기사1 요약", "기사2 요약"]}, ...]\n\n'
        f"종목 목록:\n{stocks_text}"
    )

    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            text = _extract_gemini_text(response).strip()
            if not text:
                print(f"Gemini stock analysis: empty response (attempt {attempt+1})")
                if attempt < max_attempts - 1:
                    time.sleep(5)
                    continue
                break
            result = _parse_first_json_array(text)
            if result is None:
                print(f"Gemini stock analysis: no JSON array found (attempt {attempt+1}): {text[:200]}")
                if attempt < max_attempts - 1:
                    time.sleep(5)
                    continue
                break
            return result[:len(stock_summaries)]
        except Exception as e:
            err_str = str(e)
            is_retryable = (
                "429" in err_str or "quota" in err_str.lower() or "rate" in err_str.lower()
                or "503" in err_str or "unavailable" in err_str.lower() or "overloaded" in err_str.lower()
            )
            print(f"Gemini stock analysis error (attempt {attempt+1}): {e}")
            if is_retryable and attempt < max_attempts - 1:
                wait = min(30 * (2 ** attempt), 120)  # 30, 60, 120, 120
                print(f"Gemini stock analysis: retrying in {wait}s (attempt {attempt+1}/{max_attempts})")
                time.sleep(wait)
                continue
            break
    return empty


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

def _build_headline_section(headline_news: list, summaries: list) -> str:
    if not headline_news:
        return ""
    items_html = ""
    for i, n in enumerate(headline_news):
        summary_text = summaries[i] if i < len(summaries) else n.get("desc", "")
        source = n.get("source", "")
        items_html += f"""
        <div style="padding:14px 0;border-bottom:1px solid #f3f4f6;">
          <a href="{html.escape(n.get('link', ''))}"
             style="font-size:14px;font-weight:600;color:#111827;text-decoration:none;line-height:1.4;">
            {html.escape(n.get('title', ''))}
          </a>
          {f'<span style="font-size:11px;color:#9ca3af;margin-left:6px;">{html.escape(source)}</span>' if source else ''}
          <p style="margin:6px 0 0;font-size:13px;color:#374151;line-height:1.7;">
            {html.escape(summary_text)}
          </p>
        </div>"""
    return f"""
        <section style="padding:18px 0;border-bottom:2px solid #e5e7eb;margin-bottom:4px;">
          <h2 style="margin:0 0 4px;font-size:16px;color:#111827;font-weight:700;">
            오늘의 주요 경제 뉴스
          </h2>
          <p style="margin:0 0 12px;font-size:12px;color:#9ca3af;">매일경제 · AI 요약</p>
          {items_html}
        </section>"""


def _build_digest_html(user_email: str, summaries: list, sent_at: datetime, uid: str = "") -> str:
    analyses = _gemini_stock_analysis(summaries)

    rows = []
    for i, item in enumerate(summaries):
        quote = item.get("quote") or {}
        currency = quote.get("11. currency") or "KRW"
        price = _format_digest_price(quote.get("05. price"), currency)
        change = _format_digest_change(quote.get("09. change"), quote.get("10. change percent"), currency)
        change_val = quote.get("09. change")
        change_color = "#16a34a" if change_val and float(change_val) >= 0 else "#dc2626"

        analysis = analyses[i] if i < len(analyses) else {}
        comment = analysis.get("comment", "")
        news_item_summaries = analysis.get("news_items", [])

        comment_html = f"""
          <div style="margin-top:14px;">
            <div style="font-size:11px;font-weight:700;color:#6b7280;letter-spacing:0.05em;margin-bottom:6px;">투자 의견</div>
            <div style="padding:10px 14px;background:#f0f9ff;border-left:3px solid #2563eb;border-radius:0 6px 6px 0;font-size:13px;color:#1e40af;line-height:1.7;">
              📌 {html.escape(comment)}
            </div>
          </div>""" if comment else ""

        news_items = item.get("news") or []
        news_rows = ""
        for j, n in enumerate(news_items):
            summary = news_item_summaries[j] if j < len(news_item_summaries) else ""
            news_rows += f"""
            <div style="padding:10px 0;border-bottom:1px solid #f3f4f6;">
              <a href="{html.escape(n.get('url', ''))}" style="font-size:13px;font-weight:600;color:#111827;text-decoration:none;line-height:1.5;">
                → {html.escape(n.get('title', ''))}
              </a>
              <span style="font-size:11px;color:#9ca3af;margin-left:6px;">{html.escape(n.get('source', ''))}</span>
              {f'<p style="margin:5px 0 0;font-size:12px;color:#4b5563;line-height:1.7;">{html.escape(summary)}</p>' if summary else ''}
            </div>"""
        news_section_html = f"""
          <div style="margin-top:14px;">
            <div style="font-size:11px;font-weight:700;color:#6b7280;letter-spacing:0.05em;margin-bottom:6px;">뉴스 요약</div>
            {news_rows or '<div style="font-size:12px;color:#9ca3af;">관련 뉴스가 없습니다.</div>'}
          </div>""" if news_items else ""

        rows.append(f"""
        <section style="padding:20px 0;border-bottom:1px solid #e5e7eb;">
          <div style="display:flex;align-items:baseline;flex-wrap:wrap;gap:8px;">
            <span style="font-size:17px;font-weight:700;color:#111827;">{html.escape(item.get("name") or "-")}</span>
            <span style="font-size:12px;color:#9ca3af;">{html.escape(item.get("symbol") or "")}</span>
            <span style="font-size:15px;font-weight:700;color:#111827;margin-left:4px;">{price}</span>
            <span style="font-size:13px;font-weight:600;color:{change_color};">{change}</span>
          </div>
          {comment_html}
          {news_section_html}
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
        <p style="margin:16px 0 0;font-size:12px;color:#6b7280;text-align:center;">
          메일 수신 설정은 MarketPulse 내 계정에서 변경할 수 있습니다.
          {f'&nbsp;·&nbsp;<a href="https://stockboard-fhh4.onrender.com/api/unsubscribe?uid={urllib.parse.quote(uid)}&token={_generate_unsubscribe_token(uid)}" style="color:#9ca3af;">수신 해지</a>' if uid else ''}
        </p>
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

def _generate_unsubscribe_token(uid: str) -> str:
    secret = os.environ.get("CRON_SECRET", "")
    return hmac.new(secret.encode(), uid.encode(), hashlib.sha256).hexdigest()


def _parse_digest_hour(value) -> int | None:
    try:
        hour = int(value)
    except (TypeError, ValueError):
        return None
    if 0 <= hour <= 23:
        return hour
    return None

def _run_digest_job(dry_run: bool = False, include_details: bool = False, force: bool = False) -> dict:
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
        if not force and digest_hour != current_hour:
            stats["skipped"] += 1
            stats["skip_reasons"]["hour_mismatch"] += 1
            if include_details:
                stats["details"].append({"uid": doc.id, "status": "skipped", "reason": "hour_mismatch", "configured_hour": digest_hour})
            continue
        if not force and digest.get("lastSentDate") == today:
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
        # 연속 Gemini 호출 시 rate limit 방지: 첫 번째 사용자 이후 10초 대기
        if stats["eligible"] > 1:
            time.sleep(10)
        try:
            summaries = [_build_stock_digest(stock) for stock in favorites]
            body = _build_digest_html(email, summaries, now, doc.id)
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

@app.get("/api/unsubscribe", response_class=HTMLResponse)
def unsubscribe(uid: str = Query(...), token: str = Query(...)):
    expected = _generate_unsubscribe_token(uid)
    if not hmac.compare_digest(expected, token):
        return HTMLResponse(
            "<html><body style='font-family:sans-serif;text-align:center;padding:60px'>"
            "<h2>유효하지 않은 링크입니다.</h2>"
            "<p>링크가 만료되었거나 올바르지 않습니다.</p>"
            "</body></html>",
            status_code=400,
        )
    if not _init_firebase_admin():
        return HTMLResponse(
            "<html><body style='font-family:sans-serif;text-align:center;padding:60px'>"
            "<h2>처리 중 오류가 발생했습니다.</h2><p>잠시 후 다시 시도해 주세요.</p>"
            "</body></html>",
            status_code=503,
        )
    try:
        db = _get_firestore_client()
        db.collection("users").document(uid).set(
            {"emailDigest": {"enabled": False}}, merge=True
        )
    except Exception as e:
        return HTMLResponse(
            "<html><body style='font-family:sans-serif;text-align:center;padding:60px'>"
            f"<h2>처리 중 오류가 발생했습니다.</h2><p>{html.escape(str(e))}</p>"
            "</body></html>",
            status_code=500,
        )
    return HTMLResponse(
        "<html><body style='font-family:sans-serif;text-align:center;padding:60px;"
        "background:#f3f4f6'>"
        "<div style='max-width:480px;margin:0 auto;background:#fff;border-radius:10px;"
        "padding:40px;box-shadow:0 1px 4px rgba(0,0,0,.08)'>"
        "<h2 style='color:#111827'>수신 해지 완료</h2>"
        "<p style='color:#6b7280'>MarketPulse 뉴스레터 수신이 해지되었습니다.<br>"
        "설정은 언제든지 MarketPulse 계정에서 다시 변경할 수 있습니다.</p>"
        "<a href='https://portfolio-4ffcf.web.app' style='display:inline-block;"
        "margin-top:20px;background:#2563eb;color:#fff;text-decoration:none;"
        "padding:10px 24px;border-radius:8px;font-size:14px'>MarketPulse 홈으로</a>"
        "</div></body></html>"
    )


@app.post("/api/cron/digest")
def run_digest_cron(
    x_cron_secret: str = Header(None),
    dry_run: bool = Query(False),
    include_details: bool = Query(False),
    force: bool = Query(False),
):
    cron_secret = os.environ.get("CRON_SECRET")
    if not cron_secret:
        raise HTTPException(status_code=503, detail="CRON_SECRET is not configured")
    if x_cron_secret != cron_secret:
        raise HTTPException(status_code=403, detail="Forbidden")
    return _run_digest_job(dry_run=dry_run, include_details=include_details, force=force)


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
    try:
        users = []
        for u in admin_auth.list_users().iterate_all():
            users.append({
                "uid": u.uid,
                "email": u.email or "",
                "last_sign_in": u.user_metadata.last_sign_in_timestamp,
                "created": u.user_metadata.creation_timestamp,
            })
        users.sort(key=lambda x: x["last_sign_in"] or 0, reverse=True)
        return users
    except Exception as e:
        print(f"admin_list_users error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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

@app.post("/api/admin/digest/force")
def admin_force_digest(background_tasks: BackgroundTasks, authorization: str = Header(None)):
    if not _init_firebase_admin():
        raise HTTPException(status_code=503, detail="Admin SDK not configured")
    _verify_admin(authorization)
    background_tasks.add_task(_run_digest_job, force=True)
    return {"status": "started"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
