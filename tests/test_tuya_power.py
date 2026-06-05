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
