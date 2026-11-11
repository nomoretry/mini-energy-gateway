"""Wires the components together and creates the FastAPI application.

Run with:  python -m gateway        (or: uvicorn gateway.main:app)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api.rest import build_router
from .config import Settings
from .hal.modbus_reader import ModbusReader
from .mqtt.publisher import MqttPublisher
from .services.poller import Poller
from .services.store import MeasurementStore


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    # pymodbus logs every failed connection attempt; the Poller already logs state changes.
    logging.getLogger("pymodbus").setLevel(logging.CRITICAL)

    # Data is "stale" once three poll cycles in a row have been missed (FR-13).
    store = MeasurementStore(stale_after_s=3 * settings.poll_interval_s)
    reader = ModbusReader(settings.modbus_host, settings.modbus_port, settings.modbus_unit_id)
    poller = Poller(reader, store, settings.device_id, settings.poll_interval_s)
    publisher = MqttPublisher(
        store,
        settings.mqtt_host,
        settings.mqtt_port,
        settings.readings_topic,
        settings.status_topic,
        settings.publish_interval_s,
        settings.mqtt_username,
        settings.mqtt_password,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        poller.start()
        publisher.start()
        yield
        publisher.stop()
        poller.stop()
        reader.close()

    app = FastAPI(
        title="Mini Energy Gateway",
        description="Reads a solar inverter over Modbus TCP and exposes the readings via REST and MQTT.",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.include_router(build_router(store, settings.api_key))
    if settings.api_key is None:
        logging.getLogger(__name__).warning("API_KEY is not set: the REST API is open to every client")
    return app


app = create_app()
