from fastapi import APIRouter

from app.api.v1.endpoints import (
    channels,
    gifts,
    scrapers,
    voice,
)
from app.api.v1.endpoints import etf as etf_endpoints
from app.api.v1.endpoints import finmind as finmind_endpoints
from app.api.v1.endpoints import internal as internal_endpoints
from app.api.v1.endpoints import kestrel as platform_endpoints
from app.api.v1.endpoints import tdcc as tdcc_endpoints
from app.api.v1.endpoints import twse as twse_endpoints
from app.api.v1.endpoints import yfinance as yfinance_endpoints

v1_router = APIRouter()

# Internal (health, observability)
v1_router.include_router(internal_endpoints.router)

# Data providers
v1_router.include_router(finmind_endpoints.router)
v1_router.include_router(yfinance_endpoints.router)
v1_router.include_router(twse_endpoints.router)
v1_router.include_router(tdcc_endpoints.router)
v1_router.include_router(etf_endpoints.router)
v1_router.include_router(gifts.router)

# Platform (auth, user, agent, alerts, pets, etc.)
v1_router.include_router(platform_endpoints.router)

# Other
v1_router.include_router(channels.router)
v1_router.include_router(scrapers.router)
v1_router.include_router(voice.router)

# Server push (SSE) — news/alert/score refresh hints for all frontends
from app.push.sse import router as push_router  # noqa: E402

v1_router.include_router(push_router)
