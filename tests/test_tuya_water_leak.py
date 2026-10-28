"""Tests for Tuya water leak quirks."""

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.security import IasZone

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.tuya.mcu import TuyaMCUCluster
from zhaquirks.tuya.tuya_siren import NeoBatteryState

zhaquirks.setup()

ZCL_TUYA_LEAK = b"\x09\x4f\x02\x00\x04\x65\x01\x00\x01\x01"  # DP 101, bool, leak
ZCL_TUYA_DRY = b"\x09\x51\x02\x00\x04\x65\x01\x00\x01\x00"  # DP 101, bool, dry
ZCL_TUYA_BATTERY_LOW = b"\x09\x4e\x02\x00\x02\x66\x04\x00\x01\x03"  # DP 102, low
ZCL_TUYA_BATTERY_FULL = b"\x09\x1a\x02\x00\x02\x66\x04\x00\x01\x00"  # DP 102, full


@pytest.mark.parametrize(
    "manuf,model",
    [
        ("_TYST11_qq9mpfhw", "q9mpfhw"),
        ("_TZE200_qq9mpfhw", "TS0601"),
    ],
)
async def test_tuya_water_leak_quirk(zigpy_device_from_v2_quirk, manuf, model):
    """Test Tuya water leak quirks using IAS cluster."""
    quirked_device = zigpy_device_from_v2_quirk(manuf, model)
    ep = quirked_device.endpoints[1]

    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)
    assert isinstance(ep.ias_zone, IasZone)
    assert (
        ep.ias_zone.get(IasZone.AttributeDefs.zone_type.id)
        == IasZone.ZoneType.Water_Sensor
    )

    ias_listener = ClusterListener(ep.ias_zone)
    zcl_ias_id = IasZone.AttributeDefs.zone_status.id

    hdr, data = ep.tuya_manufacturer.deserialize(ZCL_TUYA_LEAK)
    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    assert len(ias_listener.attribute_updates) == 1
    assert ias_listener.attribute_updates[0][0] == zcl_ias_id
    assert ias_listener.attribute_updates[0][1] == IasZone.ZoneStatus.Alarm_1

    hdr, data = ep.tuya_manufacturer.deserialize(ZCL_TUYA_DRY)
    status = ep.tuya_manufacturer.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    assert len(ias_listener.attribute_updates) == 2
    assert ias_listener.attribute_updates[1][0] == zcl_ias_id
    assert ias_listener.attribute_updates[1][1] == 0

    for message, expected in (
        (ZCL_TUYA_BATTERY_LOW, NeoBatteryState.Low),
        (ZCL_TUYA_BATTERY_FULL, NeoBatteryState.Full),
    ):
        hdr, data = ep.tuya_manufacturer.deserialize(message)
        status = ep.tuya_manufacturer.handle_get_data(data.data)
        assert status == foundation.Status.SUCCESS
        assert ep.tuya_manufacturer.get("power_type") == expected
