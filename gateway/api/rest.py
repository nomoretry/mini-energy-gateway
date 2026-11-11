"""Task 4 - expose the latest readings at GET /api/measurements with FastAPI."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

from ..services.store import MeasurementStore

_EXAMPLE = {
    "device_id": "inverter01",
    "timestamp": "2026-11-03T10:15:00Z",
    "dc_voltage_v": 612.4,
    "ac_power_w": 4870.0,
    "status": "ok",
}

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def build_router(store: MeasurementStore, api_key: str | None = None) -> APIRouter:
    """Create the /api routes. If api_key is given, every request must carry it
    in the X-API-Key header; without it the API is open."""

    def require_api_key(provided: str | None = Security(_api_key_header)) -> None:
        if api_key is None:
            return
        # compare_digest: constant-time comparison, does not leak how many characters match
        if provided is None or not secrets.compare_digest(provided.encode(), api_key.encode()):
            raise HTTPException(status_code=401, detail="Missing or invalid API key")

    router = APIRouter(prefix="/api", tags=["measurements"], dependencies=[Depends(require_api_key)])

    @router.get(
        "/measurements",
        summary="Latest inverter readings",
        responses={
            200: {"content": {"application/json": {"example": _EXAMPLE}}},
            401: {"description": "Missing or invalid API key (only if API_KEY is configured)"},
            503: {"description": "No reading has been acquired from the inverter yet"},
        },
    )
    def get_measurements() -> dict:
        # Served from the store: a request never waits for a Modbus read.
        measurement = store.get_latest()
        if measurement is None:
            raise HTTPException(status_code=503, detail="No measurement available yet")
        return measurement.to_dict()

    return router
