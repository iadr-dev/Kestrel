"""Read-concurrency / contention tests for the DuckDB engine.

Validates the readers-writer lock: many concurrent readers run in parallel
(not serialized behind one mutex), reads aren't starved or corrupted by a
concurrent write, and aggregate throughput stays sane under simulated MAU-level
fan-out.

These guard the change from a single global mutex (which serialized ALL reads
and collapsed throughput ~13x under load) to the _RWLock. Run:
    pytest -m perf tests/perf/test_read_concurrency.py -v
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

pytestmark = pytest.mark.perf

_SNAPSHOT_SQL = "SELECT stock_id, AVG(close) FROM price_daily WHERE stock_id = ? GROUP BY stock_id"


class TestReadConcurrency:
    def test_parallel_reads_scale(self, large_duckdb):
        """Concurrent reads should be markedly faster than the same reads serialized.

        If reads were still behind one global mutex, the threaded run would be
        ~equal to (or slower than) serial. We require a real speedup, proving
        readers run in parallel.
        """
        n = 120

        def read(i):
            return large_duckdb._query_sync(_SNAPSHOT_SQL, [str(i % 2000)])

        # Warm the cache so neither measurement pays one-time cold-start cost.
        for i in range(10):
            read(i)

        t = time.perf_counter()
        for i in range(n):
            read(i)
        serial = time.perf_counter() - t

        t = time.perf_counter()
        with ThreadPoolExecutor(max_workers=16) as ex:
            list(ex.map(read, range(n)))
        concurrent = time.perf_counter() - t

        # Parallel readers must beat serial; allow a conservative margin for
        # scheduler/GIL overhead on small CI runners.
        assert concurrent < serial * 0.8, (
            f"reads not parallel: serial={serial*1000:.0f}ms concurrent={concurrent*1000:.0f}ms"
        )

    def test_reads_not_blocked_by_write(self, large_duckdb):
        """A burst of reads completes promptly even while a write runs."""
        def read(i):
            return large_duckdb._query_sync(_SNAPSHOT_SQL, [str(i % 2000)])

        def write():
            with large_duckdb.write_connection() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO price_daily (stock_id, date, close) VALUES (?, ?, ?)",
                    ["PERFW", "2099-12-31", 1.0],
                )

        with ThreadPoolExecutor(max_workers=16) as ex:
            futures = [ex.submit(read, i) for i in range(80)]
            futures.append(ex.submit(write))
            futures += [ex.submit(read, i) for i in range(80)]
            results = [f.result(timeout=30) for f in futures]  # timeout => no deadlock

        assert len(results) == 161
        rows = large_duckdb._query_sync(
            "SELECT COUNT(*) FROM price_daily WHERE stock_id = 'PERFW'", None
        )
        assert rows[0][0] == 1

    @pytest.mark.asyncio
    async def test_async_fanout_throughput(self, large_duckdb):
        """Simulate MAU-style fan-out: many aquery() calls at once via the event loop."""
        n = 200

        async def one(i):
            return await large_duckdb.aquery(_SNAPSHOT_SQL, [str(i % 2000)])

        t = time.perf_counter()
        results = await asyncio.gather(*(one(i) for i in range(n)))
        elapsed = time.perf_counter() - t

        assert len(results) == n
        throughput = n / elapsed
        # Loose floor: should comfortably clear this once reads run in parallel.
        assert throughput > 50, f"throughput too low: {throughput:.0f} q/s"
