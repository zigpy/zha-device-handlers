"""Tests for Tuya quirks."""

import pytest
from zha.application import Platform
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import foundation

from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
import zhaquirks
import zhaquirks.tuya
from zhaquirks.tuya import TuyaCommand, TuyaData, TuyaDatapointData

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


async def test_tze204_cjbofhxw_din_power_meter(zigpy_device_from_v2_quirk):
    """Test datapoint mapping and electrical measurement scaling."""

    quirked = zigpy_device_from_v2_quirk("_TZE204_cjbofhxw", "TS0601")
    ep = quirked.endpoints[1]
    cluster = ep.electrical_measurement

    assert cluster.get("ac_voltage_multiplier") == 1
    assert cluster.get("ac_voltage_divisor") == 10
    assert cluster.get("ac_current_multiplier") == 1
    assert cluster.get("ac_current_divisor") == 1000
    assert cluster.get("ac_power_multiplier") == 1
    assert cluster.get("ac_power_divisor") == 10

    command = TuyaCommand(
        status=0,
        tsn=1,
        datapoints=[
            TuyaDatapointData(18, TuyaData(2398)),
            TuyaDatapointData(19, TuyaData(4108)),
            TuyaDatapointData(20, TuyaData(2288)),
        ],
    )
    status = ep.tuya_manufacturer.handle_get_data(command)
    assert status == foundation.Status.SUCCESS

    assert cluster.get("rms_current") == 2398
    assert cluster.get("active_power") == 4108
    assert cluster.get("rms_voltage") == 2288


async def test_tze204_cjbofhxw_from_diagnostics():
    """Test the _TZE204_cjbofhxw entities with a joined device."""
    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "tze204-cjbofhxw-ts0601-0x00000046.json", DEVICE_REGISTRY
        )
        sensors = {
            type(entity).__name__: entity.native_value
            for (platform, _), entity in device.platform_entities.items()
            if platform == Platform.SENSOR
        }

        assert sensors["ElectricalMeasurementActivePower"] == 329.5
        assert sensors["ElectricalMeasurementRMSCurrent"] == 1.779
        assert sensors["ElectricalMeasurementRMSVoltage"] == 225.4
