"""Tests for the Moes ZHT-SR (_TZE204_lpedvtvr) thermostat quirk."""

from unittest import mock

import pytest
import zigpy.types as t
from zigpy.zcl import foundation

from tests.common import wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.tuya import TuyaData, TuyaDatapointData, TuyaDPType
from zhaquirks.tuya.ts0601_moes_zhtsr import _decode_program, _to_bytes

zhaquirks.setup()

PLAN_HEX = "06060000c80b1e00c80d1e00c8111e00c8"
PLAN_TEXT = "06:00 20.0 | 11:30 20.0 | 13:30 20.0 | 17:30 20.0"


def test_decode_program():
    """Program bytes are decoded to readable text."""
    assert _decode_program(bytes.fromhex(PLAN_HEX)) == PLAN_TEXT
    assert _decode_program(b"") == ""


@pytest.mark.parametrize(
    "value",
    [
        PLAN_HEX,
        "06 06 00 00 c8 0b 1e 00 c8 0d 1e 00 c8 11 1e 00 c8",
        "0x" + PLAN_HEX,
        bytes.fromhex(PLAN_HEX),
        list(bytes.fromhex(PLAN_HEX)),
    ],
)
def test_to_bytes(value):
    """Hex text, bytes and lists are all accepted as program value."""
    assert _to_bytes(value) == bytes.fromhex(PLAN_HEX)


async def test_setpoint_and_limits(zigpy_device_from_v2_quirk):
    """Setpoint is written x10 and the limits allow 5 - 45 degC."""
    device = zigpy_device_from_v2_quirk("_TZE204_lpedvtvr", "TS0601")
    thermostat = device.endpoints[1].thermostat
    tuya = device.endpoints[1].tuya_manufacturer

    assert thermostat.get("abs_min_heat_setpoint_limit") == 500
    assert thermostat.get("abs_max_heat_setpoint_limit") == 4500

    with mock.patch.object(
        tuya.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as request:
        await thermostat.write_attributes({"occupied_heating_setpoint": 3300})
        await wait_for_zigpy_tasks()

    # DP 50, type value, 4 bytes, 330
    assert bytes(request.call_args.kwargs["data"]).endswith(
        bytes.fromhex("320200040000014a")
    )


@pytest.mark.parametrize("by", ["name", "id", "definition"])
async def test_write_week_program(zigpy_device_from_v2_quirk, by):
    """The weekly program is sent as a raw datapoint and cached as text."""
    device = zigpy_device_from_v2_quirk("_TZE204_lpedvtvr", "TS0601")
    tuya = device.endpoints[1].tuya_manufacturer

    attr_def = tuya.find_attribute("week_program_6")
    assert attr_def.type is t.CharacterString
    key = {"name": "week_program_6", "id": attr_def.id, "definition": attr_def}[by]

    with mock.patch.object(
        tuya.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as request:
        result = await tuya.write_attributes({key: PLAN_HEX})
        await wait_for_zigpy_tasks()

    # DP 107 (Saturday), type raw, length 17, payload
    assert bytes(request.call_args.kwargs["data"]).endswith(
        bytes.fromhex("6b00001106060000c80b1e00c80d1e00c8111e00c8")
    )
    assert result == [
        [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
    ]
    assert tuya.get("week_program_6") == PLAN_TEXT


async def test_write_week_program_with_other_attribute(zigpy_device_from_v2_quirk):
    """Program and normal attributes can be written in one call."""
    device = zigpy_device_from_v2_quirk("_TZE204_lpedvtvr", "TS0601")
    tuya = device.endpoints[1].tuya_manufacturer

    with mock.patch.object(
        tuya.endpoint, "request", return_value=foundation.Status.SUCCESS
    ):
        result = await tuya.write_attributes(
            {"week_program_1": PLAN_HEX, "child_lock": 1}
        )
        await wait_for_zigpy_tasks()

    assert len(result) == 2
    assert tuya.get("week_program_1") == PLAN_TEXT


async def test_week_program_report(zigpy_device_from_v2_quirk):
    """A raw datapoint report from the device is decoded to text."""
    device = zigpy_device_from_v2_quirk("_TZE204_lpedvtvr", "TS0601")
    tuya = device.endpoints[1].tuya_manufacturer

    data = TuyaData()
    data.dp_type = TuyaDPType.RAW
    data.function = t.uint8_t(0)
    data.raw = bytes.fromhex("060600012c0b1e00c80d1e00c8111e00c8")
    tuya._dp_2_attr_update(TuyaDatapointData(107, data))

    assert tuya.get("week_program_6") == (
        "06:00 30.0 | 11:30 20.0 | 13:30 20.0 | 17:30 20.0"
    )
