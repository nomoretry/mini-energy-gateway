"""Task 3 - read the inverter measurements over Modbus TCP with pymodbus."""

from __future__ import annotations

import logging
import math
from collections.abc import Sequence

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

from .register_map import REGISTER_MAP, Register, decode

log = logging.getLogger(__name__)


class ModbusReadError(Exception):
    """The inverter could not be reached or answered with an error."""


class ModbusReader:
    """Read-only Modbus TCP client (function code 0x03 only, NFR-11).

    The rest of the gateway only calls read() and never sees Modbus details.
    """

    def __init__(
        self,
        host: str,
        port: int = 502,
        unit_id: int = 1,
        register_map: Sequence[Register] = REGISTER_MAP,
        timeout_s: float = 3.0,
    ) -> None:
        self._unit_id = unit_id
        self._register_map = register_map
        self._client = ModbusTcpClient(host, port=port, timeout=timeout_s, retries=1)
        self._target = f"{host}:{port}"

    def read(self) -> dict[str, float]:
        """Read every register of the map and return {name: engineering value}.

        Reconnects automatically if the connection was lost (FR-12).
        """
        try:
            if not self._client.connected and not self._client.connect():
                raise ModbusReadError(f"cannot connect to {self._target}")
            return {reg.name: self._read_register(reg) for reg in self._register_map}
        except ModbusException as exc:
            self._client.close()  # force a clean reconnect on the next read
            raise ModbusReadError(f"{self._target}: {exc}") from exc

    def _read_register(self, reg: Register) -> float:
        response = self._client.read_holding_registers(
            reg.address, count=reg.count, device_id=self._unit_id
        )
        if response.isError():
            raise ModbusReadError(f"{reg.name} @ {reg.address:#06x}: {response}")
        value = decode(reg, response.registers)
        if not math.isfinite(value):  # NaN or infinity must never reach REST or MQTT
            raise ModbusReadError(f"{reg.name} @ {reg.address:#06x}: invalid value {value}")
        return value

    def close(self) -> None:
        self._client.close()
