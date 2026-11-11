"""Task 4 - expose the latest readings at GET /api/measurements with FastAPI."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..services.store import MeasurementStore

_EXAMPLE = {
    "device_id": "inverter01",
    "timestamp": "2026-11-03T10:15:00Z",
    "dc_voltage_v": 612.4,
    "ac_power_w": 4870.0,
    "status": "ok",
}


def build_router(store: MeasurementStore) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["measurements"])

    @router.get(
        "/measurements",
        summary="Latest inverter readings",
        responses={
            200: {"content": {"application/json": {"example": _EXAMPLE}}},
            503: {"description": "No reading has been acquired from the inverter yet"},
        },
    )
    def get_measurements() -> dict:
        # Served from the store: a request never waits for a Modbus read (NFR-01).
        measurement = store.get_latest()
        if measurement is None:
            raise HTTPException(status_code=503, detail="No measurement available yet")
        return measurement.to_dict()

    return router
