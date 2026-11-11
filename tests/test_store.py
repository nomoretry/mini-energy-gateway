import time
from datetime import datetime, timezone

from gateway.models import Measurement
from gateway.services.store import MeasurementStore


def sample() -> Measurement:
    return Measurement(
        "inverter01",
        datetime(2026, 11, 3, 10, 15, tzinfo=timezone.utc),
        {"dc_voltage_v": 612.4, "ac_power_w": 4870.0},
    )


def test_empty_store_returns_none():
    assert MeasurementStore(stale_after_s=15).get_latest() is None


def test_fresh_measurement_is_ok():
    store = MeasurementStore(stale_after_s=15)
    store.update(sample())
    assert store.get_latest().status == "ok"


def test_failed_poll_keeps_last_values_and_reports_error():
    store = MeasurementStore(stale_after_s=15)
    store.update(sample())
    store.mark_failed()
    latest = store.get_latest()
    assert latest.status == "error"
    assert latest.values["dc_voltage_v"] == 612.4


def test_old_measurement_becomes_stale():
    store = MeasurementStore(stale_after_s=0.05)
    store.update(sample())
    time.sleep(0.1)
    assert store.get_latest().status == "stale"


def test_successful_poll_clears_the_error():
    store = MeasurementStore(stale_after_s=15)
    store.update(sample())
    store.mark_failed()
    store.update(sample())
    assert store.get_latest().status == "ok"


def test_payload_format():
    assert sample().to_dict() == {
        "device_id": "inverter01",
        "timestamp": "2026-11-03T10:15:00Z",
        "dc_voltage_v": 612.4,
        "ac_power_w": 4870.0,
        "status": "ok",
    }
