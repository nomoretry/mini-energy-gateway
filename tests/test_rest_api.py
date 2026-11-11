from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from gateway.api.rest import build_router
from gateway.models import Measurement
from gateway.services.store import MeasurementStore


def make_client(store: MeasurementStore, api_key: str | None = None) -> TestClient:
    app = FastAPI()
    app.include_router(build_router(store, api_key))
    return TestClient(app)


def store_with_reading() -> MeasurementStore:
    store = MeasurementStore(stale_after_s=15)
    store.update(
        Measurement(
            "inverter01",
            datetime(2026, 11, 3, 10, 15, tzinfo=timezone.utc),
            {"dc_voltage_v": 612.4, "ac_power_w": 4870.0},
        )
    )
    return store


def test_api_key_missing_or_wrong_is_rejected():
    client = make_client(store_with_reading(), api_key="secret")
    assert client.get("/api/measurements").status_code == 401
    assert client.get("/api/measurements", headers={"X-API-Key": "wrong"}).status_code == 401


def test_api_key_correct_is_accepted():
    client = make_client(store_with_reading(), api_key="secret")
    response = client.get("/api/measurements", headers={"X-API-Key": "secret"})
    assert response.status_code == 200
    assert response.json()["dc_voltage_v"] == 612.4


def test_api_is_open_when_no_key_is_configured():
    assert make_client(store_with_reading()).get("/api/measurements").status_code == 200


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
