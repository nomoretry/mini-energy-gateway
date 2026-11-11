"""Modbus TCP simulator of a solar inverter (alternative to ModRSsim2 / diagslave).

Holding registers (float32, high word first):
    0x0010-0x0011  DC voltage [V]
    0x0020-0x0021  AC power   [W]

The values change over time so that the gateway output is visibly live.

Run with:  python simulator/inverter_sim.py [--port 5020]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import math
import random
import struct
import time

from pymodbus.server import ModbusTcpServer
from pymodbus.simulator import DataType, SimData, SimDevice

DC_VOLTAGE_ADDR = 0x0010
AC_POWER_ADDR = 0x0020
DAY_LENGTH_S = 120  # one simulated "day" takes two minutes


def simulated_values() -> tuple[float, float]:
    sun = max(0.0, math.sin(2 * math.pi * (time.time() % DAY_LENGTH_S) / DAY_LENGTH_S))
    dc_voltage = 580.0 + 40.0 * sun + random.uniform(-1.5, 1.5)
    ac_power = 5000.0 * sun + random.uniform(0.0, 20.0)
    return dc_voltage, ac_power


def float32_words(value: float) -> tuple[int, int]:
    return struct.unpack(">HH", struct.pack(">f", value))


async def refresh_registers(function_code, start_address, address, count, registers, set_values):
    """Called by pymodbus on every request: write fresh values before they are read."""
    dc_voltage, ac_power = simulated_values()
    for addr, value in ((DC_VOLTAGE_ADDR, dc_voltage), (AC_POWER_ADDR, ac_power)):
        offset = addr - start_address
        registers[offset : offset + 2] = float32_words(value)
    return None


async def main(host: str, port: int) -> None:
    device = SimDevice(
        id=1,
        simdata=[SimData(0, count=100, values=0, datatype=DataType.REGISTERS)],
        action=refresh_registers,
    )
    server = ModbusTcpServer(device, address=(host, port))
    logging.info("Inverter simulator listening on %s:%s (unit id 1)", host, port)
    await server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5020)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    try:
        asyncio.run(main(args.host, args.port))
    except KeyboardInterrupt:
        pass
