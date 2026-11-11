"""Task 5 - publish the readings as JSON to MQTT every 5 seconds with paho-mqtt."""

from __future__ import annotations

import json
import logging
import threading
import time

import paho.mqtt.client as mqtt

from ..services.store import MeasurementStore

log = logging.getLogger(__name__)


class MqttPublisher:
    def __init__(
        self,
        store: MeasurementStore,
        host: str,
        port: int,
        readings_topic: str,
        status_topic: str,
        interval_s: float = 5.0,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        self._store = store
        self._host, self._port = host, port
        self._readings_topic = readings_topic
        self._status_topic = status_topic
        self._interval_s = interval_s

        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        if username:
            self._client.username_pw_set(username, password)
        # Last will: the broker announces "offline" if the gateway dies (FR-14).
        self._client.will_set(status_topic, "offline", qos=1, retain=True)
        self._client.reconnect_delay_set(min_delay=1, max_delay=10)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect

        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="mqtt-publisher", daemon=True)

    def start(self) -> None:
        # connect_async + loop_start: paho connects and reconnects in its own
        # thread, so the gateway also starts while the broker is down (NFR-04).
        self._client.connect_async(self._host, self._port, keepalive=30)
        self._client.loop_start()
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)
        if self._client.is_connected():
            self._client.publish(self._status_topic, "offline", qos=1, retain=True).wait_for_publish(2)
        self._client.disconnect()
        self._client.loop_stop()

    def publish_once(self) -> bool:
        """Publish the latest measurement; returns False if nothing was sent."""
        measurement = self._store.get_latest()
        if measurement is None or not self._client.is_connected():
            return False
        self._client.publish(self._readings_topic, json.dumps(measurement.to_dict()), qos=1)
        return True

    def _run(self) -> None:
        next_publish = time.monotonic()
        while not self._stop.is_set():
            self.publish_once()
            next_publish += self._interval_s
            self._stop.wait(max(0.0, next_publish - time.monotonic()))

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code.is_failure:
            log.error("MQTT connection refused: %s", reason_code)
            return
        log.info("MQTT connected to %s:%s", self._host, self._port)
        client.publish(self._status_topic, "online", qos=1, retain=True)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties) -> None:
        if not self._stop.is_set():
            log.warning("MQTT connection lost (%s), reconnecting", reason_code)
