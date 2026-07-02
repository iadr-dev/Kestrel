# Database Migrations (Alembic)

The relational schema (users, portfolios, watchlists, alerts, sessions, memory,
observability traces, pets) is owned by SQLAlchemy models and versioned here.

> Scope: this covers the **SQLAlchemy** DB only. Market data lives in DuckDB
> (`market_data.duckdb`) and theme/supply-chain data in `data/*.json` — neither
> is managed by Alembic.

## Workflow

```bash
# 1. Change/add an ORM model under app/models or app/agent/**/models.py
#    (make sure it's imported in app/models/registry.py)

# 2. Autogenerate a migration from the model diff
uv run alembic revision --autogenerate -m "describe change"

# 3. Review the generated file in alembic/versions/ — autogenerate is not perfect
#    (check column types, server defaults, data migrations).

# 4. Apply
uv run alembic upgrade head

# Roll back one step
uv run alembic downgrade -1
```

The DB URL comes from `Settings().database_url` (env `DATABASE_URL`), so migrations
target whatever the app targets. SQLite uses batch mode for ALTERs automatically.

## Relationship to `create_tables()`

`app.db.session.create_tables()` calls `Base.metadata.create_all` for dev/first-run
convenience. It only *adds missing tables* — it never alters existing ones. For any
schema change to an existing table, use a migration; do not rely on `create_all`.
