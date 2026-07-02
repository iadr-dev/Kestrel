FROM python:3.12-slim AS base

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml ./
RUN uv pip install --system --no-cache .

COPY . .

EXPOSE 8000

RUN chmod +x scripts/entrypoint.sh
CMD ["./scripts/entrypoint.sh"]
