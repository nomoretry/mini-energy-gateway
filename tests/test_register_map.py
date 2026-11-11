import pytest

from gateway.hal.register_map import REGISTER_MAP, Register, decode, encode_float32


def test_register_addresses_match_the_exercise():
    by_name = {reg.name: reg for reg in REGISTER_MAP}
    assert by_name["dc_voltage_v"].address == 0x0010
    assert by_name["ac_power_w"].address == 0x0020


def test_float32_is_decoded_high_word_first():
    reg = Register("dc_voltage_v", 0x0010, "V")
    # 612.5 = 0x44192000 in IEEE 754
    assert decode(reg, [0x4419, 0x2000]) == 612.5


def test_float32_roundtrip():
    reg = Register("ac_power_w", 0x0020, "W", decimals=1)
    assert decode(reg, encode_float32(4870.3)) == 4870.3


def test_int16_with_scale_factor():
    reg = Register("dc_voltage_v", 0x0010, "V", data_type="int16", scale=0.1, decimals=1)
    assert decode(reg, [6124]) == 612.4
    assert decode(reg, [0xFFFF]) == -0.1


def test_wrong_register_count_is_rejected():
    with pytest.raises(ValueError):
        decode(Register("dc_voltage_v", 0x0010, "V"), [0x4419])
