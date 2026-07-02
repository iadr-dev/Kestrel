# Feature: Self-Built Data — ✅ FULLY DONE

## Status: COMPLETE

- ✅ yfinance API provider: `YFinanceProvider` with 8 methods (info, calendar, financials, holders, insiders, recommendations, earnings_dates, news) — replaces old Yahoo HTML scraper
- ✅ MOPS profile scraper: `get_company_info()` (chairman, HQ, founded, capital, website) — with tests
- ✅ Batch scraper: `scripts/scrape_profiles.py` with `scrape_batch()` for testing
- ✅ Theme classification: `scripts/classify_themes.py` with LLM discovery (Gemini Flash)
- ✅ 47 themes + 6815 stock-theme mappings from FinMind TaiwanStockIndustryChain
- ✅ Company profile API: `GET /themes/company/{id}/profile` (scrapes live if not cached)
- ✅ Admin Control Panel: manual trigger UI for all jobs (settings → Admin Control)
- ✅ Backend admin endpoints: `POST /admin/jobs/{job-name}` (admin-gated, 6 jobs)
- ✅ Data status dashboard: shows latest dates + record counts for all DuckDB tables
- ✅ yfinance works for BOTH US + TW stocks (auto-resolves 2330 → 2330.TW)
- ✅ 8 new `/international/yf/{ticker}/*` endpoints (info, calendar, earnings, recommendations, holders, insiders, financials, news)
- ✅ 10 live tests passing: AAPL, 2330, NVDA, MSFT, TSLA, GOOGL, AMZN, META
- ✅ Old Yahoo HTML scraper deleted (replaced by yfinance API)
- ⏭️ FMP provider: Not needed (yfinance covers all US data)

## Overview

Three critical data gaps that aistockmap solved and we must too:
1. **US Fundamentals** (earnings, dividends, institutional) — scraper
2. **Company Profiles** (CEO, HQ, founded, website) — scraper
3. **Theme/概念股 Groupings** — LLM classification + TaiwanStockIndustryChain base

---

## 1. US Stock Fundamentals (Scraper)

### Data Needed
| Field | Source | Update Frequency |
|-------|--------|-----------------|
| Revenue (quarterly) | Yahoo Finance / FMP | Quarterly |
| EPS | Yahoo Finance / FMP | Quarterly |
| P/E ratio | Yahoo Finance (real-time) | Daily |
| Dividend yield | Yahoo Finance | Quarterly |
| Market cap | FinMind USStockInfo (already have `MarketCap`) | Daily |
| 52-week range | Computed from USStockPrice (we have this) | Daily |
| Analyst target price | Yahoo Finance | Weekly |
| Institutional holders (top 10) | Yahoo Finance | Quarterly |

### Implementation: Yahoo Finance Scraper

```python
# app/scrapers/yahoo_finance.py
import httpx
from bs4 import BeautifulSoup

class YahooFinanceScraper:
    """Scrape US stock fundamentals from Yahoo Finance."""
    
    BASE = "https://finance.yahoo.com"
    
    async def get_fundamentals(self, ticker: str) -> dict:
        """Get key stats for a US stock."""
        url = f"{self.BASE}/quote/{ticker}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers())
            # Parse: P/E, EPS, dividend yield, 52-week range, market cap
            ...
    
    async def get_profile(self, ticker: str) -> dict:
        """Get company profile (sector, industry, employees, description)."""
        url = f"{self.BASE}/quote/{ticker}/profile"
        ...
    
    async def get_financials(self, ticker: str) -> dict:
        """Get income statement, balance sheet."""
        url = f"{self.BASE}/quote/{ticker}/financials"
        ...
    
    async def get_holders(self, ticker: str) -> dict:
        """Get institutional holders."""
        url = f"{self.BASE}/quote/{ticker}/holders"
        ...
```

### Alternative: FMP API (Structured, Reliable)

```python
# app/providers/fmp.py (Financial Modeling Prep)
# Free tier: 250 requests/day — enough for daily update of top 50 US stocks

class FMPProvider:
    BASE = "https://financialmodelingprep.com/api/v3"
    
    async def get_income_statement(self, ticker: str, period: str = "quarter"):
        return await self._get(f"/income-statement/{ticker}?period={period}")
    
    async def get_key_metrics(self, ticker: str):
        return await self._get(f"/key-metrics-ttm/{ticker}")
    
    async def get_analyst_estimates(self, ticker: str):
        return await self._get(f"/analyst-estimates/{ticker}")
```

### Cron Schedule
- Daily 08:00 TW (after US close): Update top 50 US stock key metrics
- Weekly: Full financial statement refresh
- Quarterly: Re-fetch all fundamentals when earnings season

---

## 2. Company Profiles (TW + US)

### Taiwan — MOPS Scraper

```python
# app/scrapers/mops_profile.py
# Source: 公開資訊觀測站 → 基本資料

class MOPSProfileScraper:
    """Scrape company basic info from MOPS."""
    
    async def get_company_info(self, stock_id: str) -> dict:
        """
        Returns:
        - company_name_zh, company_name_en
        - chairman (董事長)
        - general_manager (總經理)
        - headquarters (總部地址)
        - phone, fax
        - founded_date (成立日期)
        - listed_date (上市日期)
        - capital (實收資本額)
        - website (官方網站)
        - industry (產業類別)
        - main_business (主要經營業務)
        - employee_count
        """
        # MOPS URL: https://mops.twse.com.tw/mops/web/t05st03
        # POST with co_id={stock_id}
        ...
```

### US — Yahoo Finance Profile

```python
async def get_us_profile(self, ticker: str) -> dict:
    """
    Returns:
    - company_name, sector, industry
    - full_time_employees
    - city, state, country (HQ)
    - website
    - business_summary (long description)
    - officers (CEO name, CFO name, etc.)
    """
```

### Database Schema

```sql
CREATE TABLE company_profiles (
    stock_id VARCHAR(20) PRIMARY KEY,
    market VARCHAR(5) NOT NULL,           -- "TW" | "US"
    name_zh VARCHAR(200),
    name_en VARCHAR(200),
    chairman VARCHAR(100),
    ceo VARCHAR(100),
    headquarters VARCHAR(300),
    city VARCHAR(100),
    founded_date DATE,
    listed_date DATE,
    capital BIGINT,
    website VARCHAR(300),
    industry VARCHAR(100),
    sub_industry VARCHAR(100),
    main_business TEXT,
    employee_count INTEGER,
    updated_at DATETIME
);
```

### Cron Schedule
- Weekly: Re-scrape all TW stock profiles (changes rarely — leadership/HQ)
- Monthly: US stock profiles

---

## 3. Theme/概念股 Classification (Surpass aistockmap)

### Our Approach: 3-Layer Theme System

```
Layer 1: TWSE Official (from TaiwanStockIndustryChain)
  └── "半導體", "金融保險", "電子零組件", etc. (官方分類)

Layer 2: Investment Themes (our 16 categories — LLM classified)
  └── "AI伺服器", "散熱冷卻", "先進封測", "電動車", etc. (投資題材)

Layer 3: AI Relevance Scoring (per stock per theme, 0-100)
  └── 台積電 → AI伺服器: 95, 先進封測: 80, HPC: 90
  └── 聯發科 → AI伺服器: 70, 5G通訊: 85, 手機IC: 95
```

**This surpasses aistockmap** because they only have Layer 2 (binary membership). We add:
- Official TWSE base (Layer 1) — verifiable, institutional-grade
- Multi-theme relevance scores (Layer 3) — a stock can be 95% AI伺服器 but also 60% 散熱

### Theme Taxonomy (16 Categories)

```json
// data/themes.json
[
  {"id": "ic_design", "name_zh": "IC設計", "name_en": "IC Design"},
  {"id": "semiconductor_mfg", "name_zh": "半導體製造", "name_en": "Semiconductor Manufacturing"},
  {"id": "advanced_packaging", "name_zh": "先進封測", "name_en": "Advanced Packaging & Testing"},
  {"id": "memory", "name_zh": "記憶體", "name_en": "Memory"},
  {"id": "ai_server", "name_zh": "AI伺服器", "name_en": "AI Server"},
  {"id": "thermal", "name_zh": "散熱冷卻", "name_en": "Thermal & Cooling"},
  {"id": "networking", "name_zh": "網通衛星", "name_en": "Networking & Satellite"},
  {"id": "passive_components", "name_zh": "被動元件", "name_en": "Passive Components"},
  {"id": "electronic_parts", "name_zh": "電子零組件", "name_en": "Electronic Parts"},
  {"id": "optoelectronics", "name_zh": "光學顯示", "name_en": "Optoelectronics & Display"},
  {"id": "ev", "name_zh": "電動車", "name_en": "Electric Vehicles"},
  {"id": "green_energy", "name_zh": "綠能環保", "name_en": "Green Energy"},
  {"id": "smart_robotics", "name_zh": "智慧機器人", "name_en": "Smart Robotics"},
  {"id": "software_security", "name_zh": "軟體資安", "name_en": "Software & Cybersecurity"},
  {"id": "consumer", "name_zh": "消費終端", "name_en": "Consumer Electronics"},
  {"id": "diversified", "name_zh": "多元產業", "name_en": "Diversified"}
]
```

### Classification Prompt

```python
CLASSIFY_PROMPT = """
你是台灣股市產業分析專家。以下是一家公司的資訊，請將它分類到相關的投資題材中。

公司: {stock_name} ({stock_id})
TWSE產業: {twse_industry}
子產業: {sub_industry}
主營業務: {main_business}
近期新聞摘要: {recent_news_summary}

可選題材 (可多選，每個標註 relevance 0-100):
{themes_list}

輸出 JSON:
[
  {"theme_id": "ai_server", "relevance": 85, "reason": "主要客戶為雲端大廠，伺服器散熱模組"},
  {"theme_id": "thermal", "relevance": 95, "reason": "核心業務即散熱解決方案"}
]

規則:
- 只選真正相關的 (relevance >= 50)
- relevance 95-100: 核心業務就是這個題材
- relevance 70-94: 重要業務線，但非唯一
- relevance 50-69: 有關聯但非主力
- < 50: 不要列出
"""
```

### Weekly Update Pipeline

```python
# scripts/classify_themes.py

async def classify_all():
    # 1. Fetch TaiwanStockIndustryChain as base (Layer 1)
    industry_data = await finmind.fetch("TaiwanStockIndustryChain")
    
    # 2. Fetch company profiles for business descriptions
    profiles = await db.get_all_profiles()
    
    # 3. For each stock, LLM classify into themes (Layer 2 + 3)
    for stock in top_200_stocks:
        context = build_classification_context(stock, industry_data, profiles)
        result = await llm_classify(context)
        await db.upsert_theme_memberships(stock.id, result)
    
    # 4. Compute theme-level stats (avg change %, stock count)
    await compute_theme_stats()
```

---

## Files to Create

### Scrapers
- `app/scrapers/yahoo_finance.py` — US fundamentals + profiles
- `app/scrapers/mops_profile.py` — TW company profiles
- `app/scrapers/fmp.py` (optional) — Structured US data API

### Models
- `app/models/company_profile.py` — CompanyProfile SQLAlchemy model
- `app/models/theme.py` — Theme + ThemeMembership models

### Scripts
- `scripts/scrape_tw_profiles.py` — Batch scrape TW company info
- `scripts/scrape_us_fundamentals.py` — Batch scrape US data
- `scripts/classify_themes.py` — LLM theme classification

### Data
- `data/themes.json` — 16 theme definitions
- `data/supply_chain/` — (from feat-supply-chain.md)

### API Endpoints
- `GET /api/v1/company/{stock_id}/profile` — Company details
- `GET /api/v1/themes` — All themes with stats
- `GET /api/v1/themes/{id}/stocks` — Stocks in a theme with relevance scores

---

## Cost Estimate

| Task | Method | Cost | Frequency |
|------|--------|------|-----------|
| TW profiles (1800 stocks) | MOPS scraper | $0 | Weekly |
| US profiles (50 stocks) | Yahoo scraper | $0 | Monthly |
| US fundamentals (50 stocks) | Yahoo/FMP | $0 (free tier) | Daily |
| Theme classification (200 stocks) | Gemini Flash LLM | $0.20 | Weekly |
| **Total monthly** | | **~$0.80** | |
