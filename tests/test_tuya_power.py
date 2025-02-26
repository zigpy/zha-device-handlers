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
async def test_multi_dp_power_meter(
    zigpy_device_from_v2_quirk,
    msg,
    attr_suffix,
    expected_power,
    expected_current,
    expected_volt,
):
    """Test handling of multiple attributes mapped to the same tuya datapoint."""

    quirked = zigpy_device_from_v2_quirk("_TZE200_nslr42tt", "TS0601")
    ep = quirked.endpoints[1]

    hdr, data = ep.tuya_manufacturer.deserialize(msg)
    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    electrical_meas_cluster = ep.electrical_measurement
    assert electrical_meas_cluster.get("active_power" + attr_suffix) == expected_power
    assert electrical_meas_cluster.get("rms_current" + attr_suffix) == expected_current
    assert electrical_meas_cluster.get("rms_voltage" + attr_suffix) == expected_volt
