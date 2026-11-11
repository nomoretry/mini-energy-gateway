"""Write test values into an external Modbus TCP simulator (diagslave, ModRSsim2).

These simulators start with all registers at 0. This script writes a DC voltage
to 0x0010 and an AC power to 0x0020 as float32 (two holding registers each,
high word first), which is the format the gateway expects.

Run with:  python simulator/set_registers.py 612.5 4870 [--port 502]
"""

from __future__ import annotations

import argparse
import struct
import sys

from pymodbus.client import ModbusTcpClient

DC_VOLTAGE_ADDR = 0x0010
AC_POWER_ADDR = 0x0020


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dc_voltage", type=float, help="DC voltage in V")
    parser.add_argument("ac_power", type=float, help="AC power in W")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=502)
    parser.add_argument("--unit-id", type=int, default=1)
    args = parser.parse_args()

    client = ModbusTcpClient(args.host, port=args.port, timeout=3)
    if not client.connect():
        print(f"Cannot connect to {args.host}:{args.port}")
        return 1
    try:
        for name, address, value in (
            ("DC voltage", DC_VOLTAGE_ADDR, args.dc_voltage),
            ("AC power", AC_POWER_ADDR, args.ac_power),
        ):
            words = list(struct.unpack(">HH", struct.pack(">f", value)))
            response = client.write_registers(address, words, device_id=args.unit_id)
            if response.isError():
                print(f"{name}: write to {address:#06x} failed: {response}")
                return 1
            print(f"{name}: wrote {value} to {address:#06x}-{address + 1:#06x} as {words}")
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
