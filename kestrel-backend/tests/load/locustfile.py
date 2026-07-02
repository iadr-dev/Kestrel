"""Locust load test — simulates high-MAU traffic against the running API.

This is the "5k-10k virtual users" tier. Unlike tests/perf (in-process DB
benchmarks), this drives the *real HTTP stack* of a running server: routing,
serialization, rate limiter, cache, and the DuckDB read path under concurrency.

It is NOT a pytest — run it on demand against a server you've started separately.

    # 1. Start the API (separate terminal)
    uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

    # 2a. Headless: ramp to 5000 users, 200 spawned/sec, run 3 minutes
    uv run locust -f tests/load/locustfile.py --host http://localhost:8000 \
        --headless -u 5000 -r 200 -t 3m

    # 2b. Or open the web UI to drive it interactively
    uv run locust -f tests/load/locustfile.py --host http://localhost:8000
    #   then browse http://localhost:8089

Tuning knobs via env vars:
    KESTREL_THEME_ID   a real theme id to hit (default "半導體")
    KESTREL_EMAIL/_PW  if set, each user logs in once and sends the bearer token
                       (exercises the authenticated rate-limit path)

Install locust into the dev env first:  uv add --dev locust
"""

import os
import random

from locust import HttpUser, between, task

API = "/api/v1"
THEME_ID = os.getenv("KESTREL_THEME_ID", "半導體")
# A spread of liquid TW stock ids so cache hit/miss is realistic, not single-key.
STOCK_IDS = ["2330", "2317", "2454", "2308", "2412", "2881", "3008", "1301", "2603", "3711"]


class MarketUser(HttpUser):
    """A typical visitor: mostly browses market/theme data, rarely writes.

    Task weights mirror real read-heavy traffic — the scenario that stresses the
    DuckDB read path (the readers-writer-lock change) at high MAU.
    """

    # Think-time between requests: 1-5s, like a human clicking around.
    wait_time = between(1, 5)

    def on_start(self):
        """Optionally authenticate once so requests carry a bearer token."""
        self._headers = {}
        email, pw = os.getenv("KESTREL_EMAIL"), os.getenv("KESTREL_PW")
        if email and pw:
            r = self.client.post(
                f"{API}/auth/login",
                json={"email": email, "password": pw},
                name="auth:login",
            )
            if r.status_code == 200:
                token = r.json().get("access_token")
                if token:
                    self._headers = {"Authorization": f"Bearer {token}"}

    def _get(self, path, name):
        self.client.get(path, headers=self._headers, name=name)

    @task(10)
    def list_themes(self):
        self._get(f"{API}/themes", "themes:list")

    @task(8)
    def theme_stocks(self):
        self._get(f"{API}/themes/{THEME_ID}/stocks", "themes:stocks")

    @task(6)
    def theme_tiers(self):
        self._get(f"{API}/themes/{THEME_ID}/tiers", "themes:tiers")

    @task(6)
    def rankings(self):
        self._get(f"{API}/ai/rankings", "ai:rankings")

    @task(5)
    def stock_score(self):
        sid = random.choice(STOCK_IDS)
        self._get(f"{API}/ai/score/{sid}", "ai:score")

    @task(4)
    def stock_summary(self):
        sid = random.choice(STOCK_IDS)
        self._get(f"{API}/ai/summary/{sid}", "ai:summary")

    @task(3)
    def supply_chain_graph(self):
        self._get(f"{API}/themes/supply-chain/graph/{THEME_ID}", "themes:graph")

    @task(2)
    def search(self):
        self._get(f"{API}/themes/search?q=半導", "themes:search")

    @task(1)
    def health(self):
        self._get(f"{API}/health", "health")
