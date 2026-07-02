"""Theme discovery cron — finds emerging investment themes from news/events.

Runs weekly (after the FinMind base seed). Writes newly discovered themes to
DuckDB with status='proposed'. Supersedes the old classify_themes.py LLM block.

Usage: python -m scripts.discover_themes
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logging import get_logger
from app.services.platform.theme_discovery import discover_themes

logger = get_logger(__name__)


async def run() -> dict:
    return await discover_themes()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    result = asyncio.run(run())
    print(f"Theme discovery: {result}")
