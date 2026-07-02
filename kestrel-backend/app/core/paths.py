"""Canonical filesystem paths for the backend.

Single source of truth so modules at different nesting depths never drift
(e.g. app/services/platform/*.py vs app/api/v1/endpoints/kestrel/*.py both
need the same data dir).
"""

from pathlib import Path

# This file is app/core/paths.py → parents[2] is the backend root (kestrel-backend/).
BACKEND_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = BACKEND_ROOT / "data"
SUPPLY_CHAIN_DIR = DATA_DIR / "supply_chain"

# Themes + memberships now live in DuckDB (see app/services/data/theme_repository.py).
# These remaining files are curated *seeds* consumed by scripts/seed_themes.py.
TIER_CLASSIFICATION_FILE = DATA_DIR / "tier_classification.json"
RELATIONSHIPS_FILE = SUPPLY_CHAIN_DIR / "relationships.json"
COMPANY_PROFILES_FILE = DATA_DIR / "company_profiles.json"
