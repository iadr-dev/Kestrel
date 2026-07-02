"""Integrity tests for the curated seed files that remain on disk.

Theme + membership data now live in DuckDB (seeded from FinMind). The only JSON
files left are curated *seeds*:
- tier_classification.json — editorial sub_industry → tier knowledge
- supply_chain/relationships.json — hand-curated bootstrap edges (optional)

These must be valid UTF-8 (the encoding-bug regression guard: a prior file was
Big5-encoded and crashed on Linux).

Run: pytest tests/cron/test_data_files.py -v
"""

import json

import pytest

from app.core.paths import RELATIONSHIPS_FILE, TIER_CLASSIFICATION_FILE


def _load_utf8(path):
    """Load JSON strictly as UTF-8 — raises if the file is mis-encoded (e.g. Big5)."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class TestTierClassificationSeed:
    def test_tier_file_valid_utf8(self):
        data = _load_utf8(TIER_CLASSIFICATION_FILE)
        assert "_default" in data  # fallback bucket

    def test_tier_structure(self):
        data = _load_utf8(TIER_CLASSIFICATION_FILE)
        # Each theme maps to upstream/midstream/downstream lists.
        for theme_id, tiers in data.items():
            if theme_id.startswith("_"):
                continue
            assert {"upstream", "midstream", "downstream"} <= set(tiers.keys())


class TestSupplyChainSeed:
    def test_relationships_valid_when_present(self):
        if not RELATIONSHIPS_FILE.exists():
            pytest.skip("relationships.json seed not present (now optional)")
        data = _load_utf8(RELATIONSHIPS_FILE)
        assert isinstance(data, list)
        if data:
            rel = data[0]
            for key in ("from", "to", "type"):
                assert key in rel
