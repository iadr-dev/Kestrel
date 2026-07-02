"""Public-data scrapers for Taiwan markets — TWSE, TPEx, TDCC.

These provide cross-check data and fill gaps that FinMind doesn't cover.
Each scraper follows the same async pattern and returns ScrapeResult.
"""

from dataclasses import dataclass, field


@dataclass
class ScrapeResult:
    source: str = ""
    rows_written: int = 0
    duration_ms: int = 0
    errors: list[str] = field(default_factory=list)


__all__ = ["ScrapeResult"]
