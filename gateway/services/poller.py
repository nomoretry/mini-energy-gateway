"""Cyclic acquisition: read the inverter every poll interval and update the store."""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone

from ..hal.modbus_reader import ModbusReader, ModbusReadError
from ..models import Measurement
from .store import MeasurementStore

log = logging.getLogger(__name__)


class Poller:
    def __init__(
        self, reader: ModbusReader, store: MeasurementStore, device_id: str, interval_s: float
    ) -> None:
        self._reader = reader
        self._store = store
        self._device_id = device_id
        self._interval_s = interval_s
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="poller", daemon=True)
        self._healthy: bool | None = None  # None until the first poll

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)

    def poll_once(self) -> None:
        try:
            values = self._reader.read()
        except ModbusReadError as exc:
            self._store.mark_failed()
            if self._healthy is not False:  # log state changes only, not every cycle
                log.error("Modbus read failed: %s", exc)
            self._healthy = False
            return
        self._store.update(
            Measurement(self._device_id, datetime.now(timezone.utc), values)
        )
        if self._healthy is not True:
            log.info("Modbus read ok: %s", values)
        self._healthy = True

    def _run(self) -> None:
        next_poll = time.monotonic()
        while not self._stop.is_set():
            self.poll_once()
            # fixed schedule: a slow read does not shift the following cycles
            next_poll += self._interval_s
            self._stop.wait(max(0.0, next_poll - time.monotonic()))
