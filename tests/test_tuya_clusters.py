"""Test units for new Tuya cluster framework."""

import pytest

from zhaquirks.tuya import TuyaData


def test_tuya_data_value():
    """Test tuya "Value" datatype."""

    data = b"\x02\x00\x04\x00\x00\x02\xdb"
    extra = b"extra data"

    r, rest = TuyaData.deserialize(data + extra)
    assert rest == extra

    assert r.dp_type == 2
    assert r.raw == b"\xdb\x02\x00\x00"
    assert r.payload == 731


def test_tuya_data_bool():
    """Test tuya Bool datatype."""

    data = b"\x01\x00\x01\x00"
    extra = b"extra data"

    r, rest = TuyaData.deserialize(data + extra)
    assert rest == extra

    assert r.dp_type == 1
    assert r.raw == b"\x00"
    assert not r.payload

    data = b"\x01\x00\x01\x01"
    extra = b"extra data"

    r, rest = TuyaData.deserialize(data + extra)
    assert rest == extra

    assert r.dp_type == 1
    assert r.raw == b"\x01"
    assert r.payload


def test_tuya_data_enum():
    """Test tuya Enum datatype."""

    data = b"\x04\x00\x01\x40"
    extra = b"extra data"

    r, rest = TuyaData.deserialize(data + extra)
    assert rest == extra

    assert r.dp_type == 4
    assert r.raw == b"\x40"
    assert r.payload == 0x40


def test_tuya_data_string():
    """Test tuya String datatype."""

    data = b"\x03\x00\x04Tuya"
    extra = b"extra data"

    r, rest = TuyaData.deserialize(data + extra)
    assert rest == extra

    assert r.dp_type == 3
    assert r.raw == b"Tuya"
    assert r.payload == "Tuya"


def test_tuya_data_bitmap():
    """Test tuya Bitmap datatype."""

    data = b"\x05\x00\x01\x40"
    extra = b"extra data"

    r, rest = TuyaData.deserialize(data + extra)
    assert rest == extra

    assert r.dp_type == 5
    assert r.raw == b"\x40"
    assert r.payload == 0x40

    data = b"\x05\x00\x02\x40\x02"
    r, _ = TuyaData.deserialize(data)
    r.payload == 0x4002

    data = b"\x05\x00\x04\x40\x02\x80\x01"
    r, _ = TuyaData.deserialize(data)
    r.payload == 0x40028001


def test_tuya_data_bitmap_invalid():
    """Test tuya Bitmap datatype."""

    data = b"\x05\x00\x03\x4012"
    extra = b"extra data"

    r, rest = TuyaData.deserialize(data + extra)
    assert rest == extra

    with pytest.raises(ValueError):
        r.payload
