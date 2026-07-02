"""Seed initial figures and sample events into DuckDB."""

import json
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.duckdb.engine import get_duckdb

FIGURES = [
    {
        "id": "fig-jensen-huang",
        "name_en": "Jensen Huang",
        "name_zh": "黃仁勳",
        "role": "CEO, NVIDIA",
        "category": "tech_ceo",
        "photo_url": None,
        "associated_stocks": ["NVDA", "TSM", "2330", "AVGO", "ARM"],
    },
    {
        "id": "fig-elon-musk",
        "name_en": "Elon Musk",
        "name_zh": "馬斯克",
        "role": "CEO, Tesla & SpaceX",
        "category": "tech_ceo",
        "photo_url": None,
        "associated_stocks": ["TSLA", "TWTR", "DOGE-USD", "BTC-USD"],
    },
    {
        "id": "fig-tim-cook",
        "name_en": "Tim Cook",
        "name_zh": "提姆·庫克",
        "role": "CEO, Apple",
        "category": "tech_ceo",
        "photo_url": None,
        "associated_stocks": ["AAPL", "TSM", "2317"],
    },
    {
        "id": "fig-trump",
        "name_en": "Donald Trump",
        "name_zh": "川普",
        "role": "President, United States",
        "category": "politician",
        "photo_url": None,
        "associated_stocks": ["DJT", "SPY", "QQQ", "SOXX"],
    },
    {
        "id": "fig-pelosi",
        "name_en": "Nancy Pelosi",
        "name_zh": "裴洛西",
        "role": "Speaker Emerita, US House",
        "category": "politician",
        "photo_url": None,
        "associated_stocks": ["NVDA", "AAPL", "MSFT", "GOOGL", "RBLX"],
    },
    {
        "id": "fig-powell",
        "name_en": "Jerome Powell",
        "name_zh": "鮑爾",
        "role": "Chair, Federal Reserve",
        "category": "central_bank",
        "photo_url": None,
        "associated_stocks": ["SPY", "TLT", "QQQ", "GLD"],
    },
    {
        "id": "fig-kevin-warsh",
        "name_en": "Kevin M. Warsh",
        "name_zh": "沃許",
        "role": "Former Fed Governor",
        "category": "central_bank",
        "photo_url": None,
        "associated_stocks": ["SPY", "TLT", "QQQ", "GLD"],
    },
    {
        "id": "fig-buffett",
        "name_en": "Warren Buffett",
        "name_zh": "巴菲特",
        "role": "CEO, Berkshire Hathaway",
        "category": "investor",
        "photo_url": None,
        "associated_stocks": ["BRK-B", "AAPL", "OXY", "BAC", "KO"],
    },
    {
        "id": "fig-cathie-wood",
        "name_en": "Cathie Wood",
        "name_zh": "木頭姐",
        "role": "CEO, ARK Invest",
        "category": "investor",
        "photo_url": None,
        "associated_stocks": ["ARKK", "TSLA", "COIN", "ROKU", "SQ"],
    },
    {
        "id": "fig-morris-chang",
        "name_en": "Morris Chang",
        "name_zh": "張忠謀",
        "role": "Founder, TSMC",
        "category": "taiwan",
        "photo_url": None,
        "associated_stocks": ["TSM", "2330", "3711", "2303"],
    },
    {
        "id": "fig-terry-gou",
        "name_en": "Terry Gou",
        "name_zh": "郭台銘",
        "role": "Founder, Foxconn",
        "category": "taiwan",
        "photo_url": None,
        "associated_stocks": ["2317", "AAPL", "4938", "2354"],
    },
    {
        "id": "fig-cc-wei",
        "name_en": "C.C. Wei",
        "name_zh": "魏哲家",
        "role": "CEO, TSMC",
        "category": "taiwan",
        "photo_url": None,
        "associated_stocks": ["TSM", "2330"],
    },
    {
        "id": "fig-lisa-su",
        "name_en": "Lisa Su",
        "name_zh": "蘇姿丰",
        "role": "CEO, AMD",
        "category": "tech_ceo",
        "photo_url": None,
        "associated_stocks": ["AMD", "XLNX", "TSM"],
    },
]

SAMPLE_EVENTS = [
    {
        "figure_id": "fig-jensen-huang",
        "event_date": "2026-06-01",
        "event_type": "visit",
        "title": "Jensen Huang visits Taiwan for Computex 2026",
        "description": "NVIDIA CEO Jensen Huang arrived in Taiwan for Computex keynote, announcing next-gen Blackwell Ultra chips and expanded partnerships with TSMC.",
        "primary_stock_id": "NVDA",
        "affected_stocks": ["NVDA", "TSM", "2330", "AVGO"],
        "impact_1d": 3.2,
        "impact_5d": 5.8,
        "impact_30d": 12.1,
        "sentiment": "positive",
        "importance": 9,
    },
    {
        "figure_id": "fig-trump",
        "event_date": "2026-05-28",
        "event_type": "policy",
        "title": "Trump announces new semiconductor tariffs on China",
        "description": "President Trump signed executive order imposing 60% tariffs on Chinese semiconductor imports, escalating tech cold war.",
        "primary_stock_id": "SOXX",
        "affected_stocks": ["SOXX", "NVDA", "AMD", "TSM", "2330"],
        "impact_1d": -2.8,
        "impact_5d": -1.5,
        "impact_30d": 4.2,
        "sentiment": "negative",
        "importance": 10,
    },
    {
        "figure_id": "fig-elon-musk",
        "event_date": "2026-05-20",
        "event_type": "product",
        "title": "Tesla unveils Robotaxi fleet production timeline",
        "description": "Elon Musk confirmed mass production of Robotaxi vehicles starting Q3 2026, sending TSLA shares surging in after-hours.",
        "primary_stock_id": "TSLA",
        "affected_stocks": ["TSLA", "UBER", "LYFT"],
        "impact_1d": 8.5,
        "impact_5d": 6.2,
        "impact_30d": 15.3,
        "sentiment": "positive",
        "importance": 9,
    },
    {
        "figure_id": "fig-powell",
        "event_date": "2026-05-15",
        "event_type": "speech",
        "title": "Fed signals rate cuts likely in Q3",
        "description": "Fed Chair Powell indicated that inflation data is trending favorably and rate cuts are on the table for July FOMC meeting.",
        "primary_stock_id": "SPY",
        "affected_stocks": ["SPY", "QQQ", "TLT", "GLD"],
        "impact_1d": 1.8,
        "impact_5d": 2.4,
        "impact_30d": 5.1,
        "sentiment": "positive",
        "importance": 10,
    },
    {
        "figure_id": "fig-buffett",
        "event_date": "2026-05-10",
        "event_type": "filing",
        "title": "Berkshire 13F reveals massive AAPL position increase",
        "description": "Berkshire Hathaway's Q1 13F filing shows 15% increase in Apple position, reversing prior quarter's trimming.",
        "primary_stock_id": "AAPL",
        "affected_stocks": ["AAPL", "BRK-B"],
        "impact_1d": 2.1,
        "impact_5d": 3.4,
        "impact_30d": 7.2,
        "sentiment": "positive",
        "importance": 8,
    },
    {
        "figure_id": "fig-morris-chang",
        "event_date": "2026-05-05",
        "event_type": "speech",
        "title": "Morris Chang warns of geopolitical chip supply risks",
        "description": "TSMC founder Morris Chang stated at forum that semiconductor supply chains face unprecedented geopolitical pressure.",
        "primary_stock_id": "2330",
        "affected_stocks": ["2330", "TSM", "NVDA", "AMD"],
        "impact_1d": -1.2,
        "impact_5d": -0.8,
        "impact_30d": 2.5,
        "sentiment": "negative",
        "importance": 7,
    },
    {
        "figure_id": "fig-pelosi",
        "event_date": "2026-04-28",
        "event_type": "trade",
        "title": "Pelosi purchases NVDA call options worth $1-5M",
        "description": "Congressional disclosure shows Nancy Pelosi purchased NVDA call options expiring Jan 2027, worth between $1M-$5M.",
        "primary_stock_id": "NVDA",
        "affected_stocks": ["NVDA"],
        "impact_1d": 1.5,
        "impact_5d": 4.2,
        "impact_30d": 8.8,
        "sentiment": "positive",
        "importance": 8,
    },
    {
        "figure_id": "fig-cc-wei",
        "event_date": "2026-04-20",
        "event_type": "speech",
        "title": "TSMC CEO raises 2026 revenue guidance by 10%",
        "description": "C.C. Wei at Q1 earnings call raised full-year revenue guidance citing unprecedented AI chip demand from hyperscalers.",
        "primary_stock_id": "2330",
        "affected_stocks": ["2330", "TSM", "NVDA", "AVGO"],
        "impact_1d": 4.5,
        "impact_5d": 6.1,
        "impact_30d": 11.0,
        "sentiment": "positive",
        "importance": 9,
    },
]


def seed():
    db = get_duckdb()
    db.initialize()

    with db.write_connection() as conn:
        conn.execute("DELETE FROM figures")
        conn.execute("DELETE FROM figure_events")

        for fig in FIGURES:
            conn.execute(
                "INSERT INTO figures VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    fig["id"], fig["name_en"], fig["name_zh"],
                    fig["role"], fig["category"], fig["photo_url"],
                    json.dumps(fig["associated_stocks"]),
                ],
            )

        for evt in SAMPLE_EVENTS:
            conn.execute(
                "INSERT INTO figure_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    str(uuid4()), evt["figure_id"], evt["event_date"],
                    evt["event_type"], evt["title"], evt["description"],
                    None, evt["primary_stock_id"],
                    json.dumps(evt["affected_stocks"]),
                    evt["impact_1d"], evt["impact_5d"], evt["impact_30d"],
                    evt["sentiment"], evt["importance"],
                ],
            )

    print(f"Seeded {len(FIGURES)} figures and {len(SAMPLE_EVENTS)} events.")


if __name__ == "__main__":
    seed()
