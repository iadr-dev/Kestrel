"""Daily scoring job — pre-computes AI scores for top stocks after market close.

Runs after daily_ingest (19:30 TW) to ensure fresh data is available.
Stores results in DuckDB for instant retrieval by /ai/rankings endpoint.

Usage: python -m scripts.daily_scoring
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logging import get_logger
from app.db.duckdb.engine import get_duckdb
from app.services.platform.ai_scoring import compute_daily_scores

logger = get_logger(__name__)


async def run_daily_scoring(top_n: int = 200):
    """Compute and persist scores for top N stocks."""
    db = get_duckdb()

    # Ensure scores table exists (kind column added for market-aware scoring; the
    # ALTER backfills it on DBs created before the column existed — no-op otherwise).
    with db.write_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_scores (
                stock_id VARCHAR NOT NULL,
                technical_score INTEGER,
                chip_score INTEGER,
                fundamental_score INTEGER,
                theme_score INTEGER,
                overall_score INTEGER,
                kind VARCHAR DEFAULT 'tw-stock',
                scored_at DATE DEFAULT CURRENT_DATE,
                PRIMARY KEY (stock_id)
            )
        """)
        conn.execute("ALTER TABLE stock_scores ADD COLUMN IF NOT EXISTS kind VARCHAR DEFAULT 'tw-stock'")

    results = await compute_daily_scores(top_n=top_n)

    with db.write_connection() as conn:
        for r in results:
            conn.execute("""
                INSERT OR REPLACE INTO stock_scores
                (stock_id, technical_score, chip_score, fundamental_score, theme_score, overall_score, kind, scored_at)
                VALUES (?, ?, ?, ?, ?, ?, 'tw-stock', CURRENT_DATE)
            """, [
                r["stock_id"],
                r["technical_score"],
                r["chip_score"],
                r["fundamental_score"],
                r["theme_score"],
                r["overall_score"],
            ])

    logger.info("daily_scoring_complete", stocks_scored=len(results))
    return results


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    result = asyncio.run(run_daily_scoring())
    print(f"Scored {len(result)} stocks")
