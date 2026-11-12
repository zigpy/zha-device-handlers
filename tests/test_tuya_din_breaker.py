"""Tests for the Tuya _TZE204_fhvdgeuh DIN-rail breaker with power monitoring."""

from unittest import mock

import pytest
import zigpy.types as t
from zigpy.zcl import foundation

from tests.common import wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.tuya import PowerOnState, TuyaDPType
from zhaquirks.tuya.ts0601_din_breaker import (
    SmartMeterManufCluster,
    faults_bitmap,
    faults_to_text,
    phase_current,
    phase_power,
    phase_voltage,
    status_to_text,
)

zhaquirks.setup()


def _tuya_frame(datapoints: list[tuple[int, int, bytes]]) -> bytes:
    """Build a Tuya get_data ZCL frame from (dp, dp_type, raw) datapoints."""
    frame = b"\x09\xe0\x02\x0b\x33"
    for dp, dp_type, raw in datapoints:
        frame += bytes([dp, dp_type, 0x00, len(raw)]) + raw
    return frame


def _value(value: int) -> bytes:
    return value.to_bytes(4, "big", signed=True)


@pytest.fixture
def breaker(zigpy_device_from_v2_quirk):
    """Quirked _TZE204_fhvdgeuh device."""
    return zigpy_device_from_v2_quirk("_TZE204_fhvdgeuh", "TS0601")


def _receive(cluster, datapoints):
    hdr, data = cluster.deserialize(_tuya_frame(datapoints))
    return cluster.handle_get_data(data.data)


def test_cluster(breaker):
    """Test the replacement cluster is used."""
    assert isinstance(breaker.endpoints[1].tuya_manufacturer, SmartMeterManufCluster)


async def test_measurements(breaker):
    """Test energy, phase A, temperature, leakage and relay datapoints."""
    ep = breaker.endpoints[1]
    mcu = ep.tuya_manufacturer

    # 230.5 V, 1.234 A, 284 W
    phase = bytes([0x09, 0x01, 0x00, 0x04, 0xD2, 0x00, 0x01, 0x1C])
    status = _receive(
        mcu,
        [
            (1, TuyaDPType.VALUE, _value(12345)),
            (6, TuyaDPType.RAW, phase),
            (15, TuyaDPType.VALUE, _value(7)),
            (16, TuyaDPType.BOOL, b"\x01"),
            (103, TuyaDPType.VALUE, _value(36)),
        ],
    )
    assert status == foundation.Status.SUCCESS

    assert mcu.get("energy") == 12345
    assert mcu.get("voltage") == 2305
    assert mcu.get("current") == 1234
    assert mcu.get("active_power") == 284
    assert mcu.get("leakage_current") == 7
    assert mcu.get("temperature") == 36
    assert ep.on_off.get("on_off") == 1


@pytest.mark.parametrize(
    "raw,voltage,current,power",
    [
        (bytes([0x09, 0x01, 0x00, 0x04, 0xD2, 0x00, 0x01, 0x1C]), 2305, 1234, 284),
        # negative power, offset encoding used by the device
        (bytes([0x09, 0x01, 0x00, 0x00, 0x64, 0x99, 0x99, 0x90]), 2305, 100, -10),
        # negative power, two's complement
        (bytes([0x09, 0x01, 0x00, 0x00, 0x64, 0xFF, 0xFF, 0xF6]), 2305, 100, -10),
        # short 7 byte variant: 2 byte current and power
        (bytes([0x09, 0x01, 0x00, 0x04, 0xD2, 0x01, 0x1C]), 2305, 1234, 284),
        (b"", 0, 0, 0),
    ],
)
def test_phase_converters(raw, voltage, current, power):
    """Test the phase A raw payload converters."""
    assert phase_voltage(raw) == voltage
    assert phase_current(raw) == current
    assert phase_power(raw) == power


def test_phase_converters_payload_types():
    """Test the phase converters accept serializable and list payloads."""
    raw = [0x09, 0x01, 0x00, 0x04, 0xD2, 0x00, 0x01, 0x1C]
    assert phase_voltage(raw) == 2305
    assert phase_current(bytes(raw)) == 1234
    assert phase_power(t.SerializableBytes(bytes(raw))) == 284


def test_faults_and_status():
    """Test fault bitmap normalization and text conversion."""
    # bitmap16 arrives byte-swapped: 0x0100 means bit 0 (short circuit)
    assert faults_bitmap(t.bitmap16(0x0100)) == 0x0001
    assert faults_bitmap(t.bitmap8(0x04)) == 0x04
    assert faults_bitmap(5) == 5
    assert faults_bitmap(b"\x00\x02") == 2

    assert faults_to_text(0) == "ok"
    assert faults_to_text(0b101) == "short_circuit, overload"
    assert faults_to_text(1 << 16) == "unknown_0x1"
    assert faults_to_text("overload") == "overload"
    assert faults_to_text(None) == "None"

    assert faults_to_text(b"\x00\x04") == "overload"
    assert faults_to_text(b"") == "ok"

    assert status_to_text(0) == "standby"
    assert status_to_text(1) == "active"
    assert status_to_text(7) == "unknown_7"
    assert status_to_text("active") == "active"


async def test_fault_and_status_datapoints(breaker):
    """Test faults (bitmap) and status (enum) datapoints."""
    mcu = breaker.endpoints[1].tuya_manufacturer

    status = _receive(
        mcu,
        [
            (9, TuyaDPType.BITMAP, b"\x00\x04"),
            (127, TuyaDPType.ENUM, b"\x01"),
            (134, TuyaDPType.ENUM, b"\x02"),
        ],
    )
    assert status == foundation.Status.SUCCESS
    assert faults_to_text(mcu.get("fault")) == "overload"
    assert status_to_text(mcu.get("status")) == "active"
    assert mcu.get("relay_status_for_power_on") == PowerOnState.LastState


async def test_threshold_datapoints(breaker):
    """Test alarm set datapoints update thresholds and breaker switches."""
    mcu = breaker.endpoints[1].tuya_manufacturer

    alarm_1 = bytes([0x04, 0x01, 0x00, 0x1E, 0x05, 0x00, 0x00, 0x50])
    alarm_2 = bytes(
        [0x01, 0x01, 0x01, 0x40, 0x03, 0x00, 0x01, 0x0E, 0x04, 0x01, 0x00, 0xAA]
    )
    status = _receive(
        mcu,
        [
            (17, TuyaDPType.RAW, alarm_1),
            # unknown entry type 9 is ignored
            (18, TuyaDPType.RAW, alarm_2 + bytes([0x09, 0x01, 0x00, 0x01])),
        ],
    )
    assert status == foundation.Status.SUCCESS

    assert mcu.get("leakage_threshold") == 30
    assert mcu.get("leakage_breaker") is True
    assert mcu.get("high_temperature_threshold") == 80
    assert mcu.get("high_temperature_breaker") is False
    assert mcu.get("over_current_threshold") == 320
    assert mcu.get("over_current_breaker") is True
    assert mcu.get("over_voltage_threshold") == 270
    assert mcu.get("over_voltage_breaker") is False
    assert mcu.get("under_voltage_threshold") == 170
    assert mcu.get("under_voltage_breaker") is True


async def test_threshold_write(breaker):
    """Test writing one threshold sends the full alarm set datapoint."""
    mcu = breaker.endpoints[1].tuya_manufacturer

    alarm_2 = bytes(
        [0x01, 0x01, 0x01, 0x40, 0x03, 0x00, 0x01, 0x0E, 0x04, 0x01, 0x00, 0xAA]
    )
    _receive(mcu, [(18, TuyaDPType.RAW, alarm_2)])

    with mock.patch.object(
        mcu.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as request:
        (status,) = await mcu.write_attributes({"over_voltage_threshold": 280})
        await wait_for_zigpy_tasks()

    assert status == [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
    data = request.call_args.kwargs["data"]
    expected = bytes(
        [0x01, 0x01, 0x01, 0x40, 0x03, 0x00, 0x01, 0x18, 0x04, 0x01, 0x00, 0xAA]
    )
    assert data.endswith(bytes([18, TuyaDPType.RAW, 0x00, len(expected)]) + expected)


async def test_threshold_write_unknown_entries(breaker):
    """Test entries without known values are sent as empty entries."""
    mcu = breaker.endpoints[1].tuya_manufacturer

    with mock.patch.object(
        mcu.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as request:
        await mcu.write_attributes({"leakage_threshold": 30})
        await wait_for_zigpy_tasks()

    data = request.call_args.kwargs["data"]
    expected = bytes(8)
    assert data.endswith(bytes([17, TuyaDPType.RAW, 0x00, len(expected)]) + expected)
