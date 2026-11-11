"""Data model shared by all layers."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone

STATUS_OK = "ok"  # last poll succeeded
STATUS_ERROR = "error"  # last poll failed, values are the last known good ones
STATUS_STALE = "stale"  # last successful poll is too old


@dataclass(frozen=True)
class Measurement:
    """One set of readings taken from the inverter at a point in time."""

    device_id: str
    timestamp: datetime  # UTC time of the Modbus read
    values: dict[str, float]  # e.g. {"dc_voltage_v": 612.4, "ac_power_w": 4870.0}
    status: str = STATUS_OK

    def with_status(self, status: str) -> Measurement:
        return replace(self, status=status)

    def to_dict(self) -> dict:
        """JSON payload used by both the REST API and MQTT (FR-11)."""
        return {
            "device_id": self.device_id,
            "timestamp": self.timestamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            **self.values,
            "status": self.status,
        }
