"""Thread-safe holder of the latest measurement.

Single source of truth for the REST API and the MQTT publisher: both read
from here, so neither depends on Modbus timing or on the other.
"""

from __future__ import annotations

import threading
import time

from ..models import STATUS_ERROR, STATUS_OK, STATUS_STALE, Measurement


class MeasurementStore:
    def __init__(self, stale_after_s: float) -> None:
        self._stale_after_s = stale_after_s
        self._lock = threading.Lock()
        self._latest: Measurement | None = None
        self._updated_at = 0.0  # time.monotonic() of the last successful update
        self._last_poll_failed = False

    def update(self, measurement: Measurement) -> None:
        """Store a new measurement after a successful poll."""
        with self._lock:
            self._latest = measurement
            self._updated_at = time.monotonic()
            self._last_poll_failed = False

    def mark_failed(self) -> None:
        """Record that the last poll failed; the last good values are kept."""
        with self._lock:
            self._last_poll_failed = True

    def get_latest(self) -> Measurement | None:
        """Return the latest measurement with its current status, or None if
        nothing has been read yet."""
        with self._lock:
            if self._latest is None:
                return None
            if time.monotonic() - self._updated_at > self._stale_after_s:
                status = STATUS_STALE
            elif self._last_poll_failed:
                status = STATUS_ERROR
            else:
                status = STATUS_OK
            return self._latest.with_status(status)
