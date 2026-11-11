"""Register map of the inverter and decoding of raw register words.

To add a measurement or adapt to another device, edit REGISTER_MAP only;
no other module knows register addresses or encodings (NFR-07).
"""

from __future__ import annotations

import struct
from collections.abc import Sequence
from dataclasses import dataclass

# data type -> number of 16-bit registers it occupies
_REGISTER_COUNT = {"float32": 2, "uint16": 1, "int16": 1}


@dataclass(frozen=True)
class Register:
    name: str  # field name in the JSON payload
    address: int  # zero-based protocol address (0x0010 = 40017 in 1-based tools)
    unit: str
    data_type: str = "float32"
    scale: float = 1.0  # engineering value = raw value * scale
    decimals: int = 2

    @property
    def count(self) -> int:
        return _REGISTER_COUNT[self.data_type]


REGISTER_MAP: tuple[Register, ...] = (
    Register(name="dc_voltage_v", address=0x0010, unit="V"),
    Register(name="ac_power_w", address=0x0020, unit="W", decimals=1),
)


def decode(register: Register, words: Sequence[int]) -> float:
    """Convert the raw 16-bit register words into an engineering value."""
    if len(words) != register.count:
        raise ValueError(f"{register.name}: expected {register.count} registers, got {len(words)}")
    if register.data_type == "float32":
        # two registers, high word first, combined into a big-endian IEEE 754 float
        raw = struct.unpack(">f", struct.pack(">HH", *words))[0]
    elif register.data_type == "int16":
        raw = struct.unpack(">h", struct.pack(">H", words[0]))[0]
    else:  # uint16
        raw = words[0]
    return round(raw * register.scale, register.decimals)


def encode_float32(value: float) -> list[int]:
    """Inverse of decode() for float32; used by the simulator and the tests."""
    return list(struct.unpack(">HH", struct.pack(">f", value)))
