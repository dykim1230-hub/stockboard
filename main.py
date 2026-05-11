# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import FinanceDataReader as fdr

app = FastAPI(title="Stock Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global cache for KRX and ETF listings
krx_df = None
etf_df = None

def get_krx_data():
    global krx_df, etf_df
    if krx_df is None:
        try:
            print("Loading KRX and ETF listings for search...")
            krx_df = fdr.StockListing('KRX')
            etf_df = fdr.StockListing('ETF/KR')
            print("Listings loaded successfully.")
        except Exception as e:
            print("Failed to load KRX/ETF data:", e)
    return krx_df, etf_df

def is_korean_symbol(symbol: str) -> bool:
    """Check if symbol is a Korean stock (ends with .KS or .KQ)"""
    return symbol.endswith('.KS') or symbol.endswith('.KQ')

@app.get("/api/search")
def search_stock(q: str = Query(..., description="Search query")):
    """
    Search for stocks: Korean stocks/ETFs first via FinanceDataReader,
    then international via Yahoo Finance.
    """
    if not q:
        return []

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
                    if 'KOSDAQ' in market:
                        yf_symbol = f"{code}.KQ"
                    else:
                        yf_symbol = f"{code}.KS"
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

    # International via Yahoo Finance
    if len(results) < 7:
        try:
            url = "https://query2.finance.yahoo.com/v1/finance/search"
            params = {"q": q, "quotesCount": 6, "newsCount": 0}
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            res = requests.get(url, params=params, headers=headers)
            res.raise_for_status()
            data = res.json()
            for quote in data.get("quotes", []):
                symbol = quote.get("symbol")
                if symbol and symbol not in added_symbols:
                    shortname = quote.get("shortname") or quote.get("longname") or symbol
                    results.append({
                        "1. symbol": symbol,
                        "2. name": shortname,
                        "3. currency": "USD",
                        "4. is_korean": False
                    })
                    added_symbols.add(symbol)
        except Exception as e:
            print(f"Yahoo Search API error: {e}")

    return results[:10]


@app.get("/api/quote")
def get_quote(symbol: str = Query(..., description="Stock symbol")):
    """
    Get current quote. Returns price with currency info (KRW or USD).
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        price = info.get("currentPrice") or info.get("regularMarketPrice")
        if price is None:
            hist = ticker.history(period="2d")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else price
            else:
                return None
        else:
            prev = info.get("previousClose") or info.get("regularMarketPreviousClose") or price

        price = float(price)
        prev = float(prev)
        change = price - prev
        change_pct = (change / prev * 100) if prev else 0.0

        # Detect currency from yfinance info, fallback to symbol suffix
        currency = info.get("currency", "")
        if not currency:
            currency = "KRW" if is_korean_symbol(symbol) else "USD"

        return {
            "05. price": price,
            "09. change": change,
            "10. change percent": change_pct,
            "11. currency": currency
        }
    except Exception as e:
        print(f"Quote API error for {symbol}: {e}")
        return None


@app.get("/api/chart")
def get_chart(symbol: str = Query(..., description="Stock symbol")):
    """
    Get 1-year daily OHLCV data.
    """
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1y")
        if hist.empty:
            return None
        data = {}
        for index, row in hist.iterrows():
            date_str = index.strftime("%Y-%m-%d")
            data[date_str] = {"4. close": float(row["Close"])}
        return data
    except Exception as e:
        print(f"Chart API error for {symbol}: {e}")
        return None


def _naver_news(query: str) -> list:
    """네이버 뉴스 최신순 스크래핑 - li.bx 아이템 직접 파싱"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "ko-KR,ko;q=0.9",
        }
        res = requests.get(
            "https://search.naver.com/search.naver",
            params={"where": "news", "query": query, "sort": 1},
            headers=headers,
            timeout=10
        )
        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")

        articles = []
        seen_urls = set()

        # 각 뉴스 아이템: li.bx
        for item in soup.select("li.bx"):
            if len(articles) >= 10:
                break

            title_el = item.select_one("a.news_tit")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            url = title_el.get("href", "")
            if not url or url in seen_urls:
                continue

            summary_el = item.select_one(".dsc_txt") or item.select_one(".dsc_txt_wrap")
            summary = summary_el.get_text(strip=True) if summary_el else ""

            source_el = item.select_one(".info_group a") or item.select_one(".press")
            source = source_el.get_text(strip=True) if source_el else ""

            time_el = item.select_one(".info_group span.is_blind") or item.select_one(".info_group .date")
            time_published = time_el.get_text(strip=True) if time_el else ""

            articles.append({
                "title": title,
                "summary": summary[:120] + ("..." if len(summary) > 120 else ""),
                "url": url,
                "source": source,
                "time_published": time_published
            })
            seen_urls.add(url)

        return articles
    except Exception as e:
        print(f"Naver News error for '{query}': {e}")
        return []


def _yahoo_rss_news(symbol: str) -> list:
    """Yahoo Finance RSS 피드로 해외 종목 최신 뉴스 조회"""
    import xml.etree.ElementTree as ET
    try:
        rss_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = requests.get(rss_url, headers=headers, timeout=10)
        res.raise_for_status()

        root = ET.fromstring(res.content)
        ns = {"media": "http://search.yahoo.com/mrss/"}
        articles = []

        for item in root.findall(".//item")[:10]:
            title = item.findtext("title", "").strip()
            url = item.findtext("link", "").strip()
            summary = item.findtext("description", "").strip()
            pub_date = item.findtext("pubDate", "").strip()
            source_el = item.find("source")
            source = source_el.text.strip() if source_el is not None else "Yahoo Finance"

            # HTML 태그 제거
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

        return articles
    except Exception as e:
        print(f"Yahoo RSS news error for '{symbol}': {e}")
        return []


@app.get("/api/news")
def get_news(
    stock_name: str = Query(..., description="Stock name for display/search"),
    symbol: str = Query(None, description="Stock symbol (required for international stocks)"),
    is_korean: bool = Query(True, description="Korean stock flag")
):
    """
    국내 종목: 네이버 뉴스 최신순 스크래핑
    해외 종목: yfinance 뉴스 (종목명 자동 매핑)
    """
    if is_korean:
        return _naver_news(f"{stock_name} 주식")
    else:
        if not symbol:
            return []
        return _yahoo_rss_news(symbol)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
