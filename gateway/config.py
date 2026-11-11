"""Cross-cutting: deployment settings, read from environment variables.

Every value has a default that works with the bundled simulator, so the
gateway starts without any configuration (NFR-08).
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    device_id: str = "inverter01"

    # Modbus TCP (inverter or simulator)
    modbus_host: str = "127.0.0.1"
    modbus_port: int = 5020  # real devices, ModRSsim2 and diagslave use 502
    modbus_unit_id: int = 1
    poll_interval_s: float = 5.0

    # MQTT broker (Mosquitto)
    mqtt_host: str = "127.0.0.1"
    mqtt_port: int = 1883
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    publish_interval_s: float = 5.0

    # REST API
    http_host: str = "127.0.0.1"
    http_port: int = 8000
    api_key: str | None = None  # if set, clients must send it in the X-API-Key header

    @property
    def readings_topic(self) -> str:
        return f"solar/{self.device_id}/readings"

    @property
    def status_topic(self) -> str:
        return f"solar/{self.device_id}/status"

    @classmethod
    def from_env(cls) -> Settings:
        env = os.environ.get
        return cls(
            device_id=env("GATEWAY_DEVICE_ID", cls.device_id),
            modbus_host=env("MODBUS_HOST", cls.modbus_host),
            modbus_port=int(env("MODBUS_PORT", cls.modbus_port)),
            modbus_unit_id=int(env("MODBUS_UNIT_ID", cls.modbus_unit_id)),
            poll_interval_s=float(env("POLL_INTERVAL_S", cls.poll_interval_s)),
            mqtt_host=env("MQTT_HOST", cls.mqtt_host),
            mqtt_port=int(env("MQTT_PORT", cls.mqtt_port)),
            mqtt_username=env("MQTT_USERNAME"),
            mqtt_password=env("MQTT_PASSWORD"),
            publish_interval_s=float(env("PUBLISH_INTERVAL_S", cls.publish_interval_s)),
            http_host=env("HTTP_HOST", cls.http_host),
            http_port=int(env("HTTP_PORT", cls.http_port)),
            api_key=env("API_KEY") or None,
        )
