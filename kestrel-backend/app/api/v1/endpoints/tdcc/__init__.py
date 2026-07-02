"""TDCC OpenAPI endpoints."""

from fastapi import APIRouter

from app.api.v1.endpoints.tdcc import tdcc

router = APIRouter()

router.include_router(tdcc.router)
