from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from gateway.api.rest import build_router
from gateway.models import Measurement
from gateway.services.store import MeasurementStore


def make_client(store: MeasurementStore) -> TestClient:
    app = FastAPI()
    app.include_router(build_router(store))
    return TestClient(app)


def test_returns_503_before_first_reading():
    response = make_client(MeasurementStore(stale_after_s=15)).get("/api/measurements")
    assert response.status_code == 503


def test_returns_latest_reading_as_json():
    store = MeasurementStore(stale_after_s=15)
    store.update(
        Measurement(
            "inverter01",
            datetime(2026, 11, 3, 10, 15, tzinfo=timezone.utc),
            {"dc_voltage_v": 612.4, "ac_power_w": 4870.0},
        )
    )
    response = make_client(store).get("/api/measurements")
    assert response.status_code == 200
    assert response.json() == {
        "device_id": "inverter01",
        "timestamp": "2026-11-03T10:15:00Z",
        "dc_voltage_v": 612.4,
        "ac_power_w": 4870.0,
        "status": "ok",
    }
