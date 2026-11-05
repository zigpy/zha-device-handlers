"""Tests for Tuya quirks."""

import pytest
from zigpy.zcl import foundation

import zhaquirks
import zhaquirks.tuya

zhaquirks.setup()


@pytest.mark.parametrize(
    "msg,attr_suffix,expected_power,expected_current,expected_volt",
    [
        (b"\t0\x02\x00\xd3\x06\x00\x00\x08\tn\x00\nA\x00\x01\xa6", "", 422, 2625, 2414),
        (b"\t2\x02\x00Z\x06\x00\x00\x08\ts\x00\n9\x00\x01\xa5", "", 421, 2617, 2419),
        (b"\t2\x02\x00Z\x06\x00\x00\x08\ts\x00\n9\x00\x91\xa5", "", -2037, 2617, 2419),
        (
            b"\t0\x02\x00\xd3\x07\x00\x00\x08\tn\x00\nA\x00\x01\xa6",
            "_ph_b",
            422,
            2625,
            2414,
        ),
        (
            b"\t2\x02\x00Z\x07\x00\x00\x08\ts\x00\n9\x00\x01\xa5",
            "_ph_b",
            421,
            2617,
            2419,
        ),
        (
            b"\t0\x02\x00\xd3\x08\x00\x00\x08\tn\x00\nA\x00\x01\xa6",
            "_ph_c",
            422,
            2625,
            2414,
        ),
        (
            b"\t2\x02\x00Z\x08\x00\x00\x08\ts\x00\n9\x00\x01\xa5",
            "_ph_c",
            421,
            2617,
            2419,
        ),
    ],
)
async def test_ts0601_electrical_measurement_multi_dp_converter(
    zigpy_device_from_v2_quirk,
    msg,
    attr_suffix,
    expected_power,
    expected_current,
    expected_volt,
):
    """Test converter for multiple electrical attributes mapped to the same tuya datapoint."""

    quirked = zigpy_device_from_v2_quirk("_TZE200_nslr42tt", "TS0601")
    ep = quirked.endpoints[1]

    tuya_manufacturer = ep.tuya_manufacturer
    hdr, data = tuya_manufacturer.deserialize(msg)
    status = tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    electrical_meas_cluster = ep.electrical_measurement
    assert electrical_meas_cluster.get("active_power" + attr_suffix) == expected_power
    assert electrical_meas_cluster.get("rms_current" + attr_suffix) == expected_current
    assert electrical_meas_cluster.get("rms_voltage" + attr_suffix) == expected_volt


@pytest.mark.parametrize(
    "msg,expected_power",
    [
        (b"\x19\x8a\x02\x00\x0f\t\x02\x00\x04\x00\x00\x00\x80", 128),
        (b"\x19\x8a\x02\x00\x0f\t\x02\x00\x04\x19\x99\x99\x00", -156),
    ],
)
async def test_ts0601_power_converter(zigpy_device_from_v2_quirk, msg, expected_power):
    """Test converter for power."""

    quirked = zigpy_device_from_v2_quirk("_TZE200_nslr42tt", "TS0601")
    ep = quirked.endpoints[1]

    tuya_manufacturer = ep.tuya_manufacturer
    hdr, data = tuya_manufacturer.deserialize(msg)
    status = tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    assert tuya_manufacturer.get("power") == expected_power


def _tuya_dp_value_report(seq: int, datapoints: dict[int, int]) -> bytes:
    """Build a Tuya MCU data report with one 4-byte value DP per entry."""
    payload = b"".join(
        bytes([dp, 0x02, 0x00, 0x04]) + value.to_bytes(4, "big")
        for dp, value in datapoints.items()
    )
    return bytes([0x09, seq, 0x02]) + seq.to_bytes(2, "big") + payload


@pytest.mark.parametrize(
    "manufacturer",
    ["_TZE200_gomuk3dc", "_TZE204_gomuk3dc", "_TZE284_gomuk3dc"],
)
async def test_ts0601_3phase_spm02_sdm01(zigpy_device_from_v2_quirk, manufacturer):
    """Test the Tuya SPM02 / Zemismart SDM01 3-phase energy meter datapoints."""

    quirked = zigpy_device_from_v2_quirk(manufacturer, "TS0601")
    ep = quirked.endpoints[1]
    tuya_manufacturer = ep.tuya_manufacturer
    electrical_meas_cluster = ep.electrical_measurement

    msg = _tuya_dp_value_report(
        0x10,
        {
            1: 123456,  # total energy, 0.01 kWh
            23: 789,  # total energy produced, 0.01 kWh
            29: 1500,  # total active power, W
            32: 5003,  # AC frequency, 0.01 Hz
            50: 97,  # total power factor, %
            102: 30,  # update frequency, s
            # phase A
            103: 2301,
            104: 1234,
            105: 280,
            108: 95,
            109: 4567,
            110: 12,
            # phase B
            112: 2312,
            113: 2345,
            114: 540,
            117: 88,
            118: 6789,
            119: 34,
            # phase C
            121: 2295,
            122: 3456,
            123: 680,
            126: 91,
            127: 8901,
            128: 56,
        },
    )
    hdr, data = tuya_manufacturer.deserialize(msg)
    status = tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    assert tuya_manufacturer.get("energy") == 123456
    assert tuya_manufacturer.get("energy_produced") == 789
    assert tuya_manufacturer.get("power_factor") == 97
    assert tuya_manufacturer.get("update_frequency") == 30

    assert electrical_meas_cluster.get("total_active_power") == 1500
    assert electrical_meas_cluster.get("ac_frequency") == 50.03

    for suffix, expected in {
        "": (2301, 1234, 280, 95),
        "_ph_b": (2312, 2345, 540, 88),
        "_ph_c": (2295, 3456, 680, 91),
    }.items():
        assert (
            electrical_meas_cluster.get("rms_voltage" + suffix),
            electrical_meas_cluster.get("rms_current" + suffix),
            electrical_meas_cluster.get("active_power" + suffix),
            electrical_meas_cluster.get("power_factor" + suffix),
        ) == expected

    for phase, consumed, produced in (
        ("a", 4567, 12),
        ("b", 6789, 34),
        ("c", 8901, 56),
    ):
        assert tuya_manufacturer.get(f"energy_consumed_ph_{phase}") == consumed
        assert tuya_manufacturer.get(f"energy_produced_ph_{phase}") == produced
