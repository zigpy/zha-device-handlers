"""Tests for Tuya gas quirks."""

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.security import IasZone

from tests.common import ClusterListener
import zhaquirks
import zhaquirks.tuya
from zhaquirks.tuya.mcu import TuyaMCUCluster

ZCL_TUYA_GAS_PRESENT_ENUM = b"\tL\x01\x00\x05\x01\x04\x00\x01\x00"  # DP 1, enum, gas

ZCL_TUYA_GAS_CLEAR_ENUM = b"\tL\x01\x00\x05\x01\x04\x00\x01\x01"  # DP 1, enum, clear


zhaquirks.setup()


@pytest.mark.parametrize(
    "model,manuf,gas_present,gas_clear",
    [
        (
            "_TZE200_yojqa8xn",
            "TS0601",
            ZCL_TUYA_GAS_PRESENT_ENUM,
            ZCL_TUYA_GAS_CLEAR_ENUM,
        ),
        (
            "_TZE204_zougpkpy",
            "TS0601",
            ZCL_TUYA_GAS_PRESENT_ENUM,
            ZCL_TUYA_GAS_CLEAR_ENUM,
        ),
        (
            "_TZE204_chbyv06x",
            "TS0601",
            ZCL_TUYA_GAS_PRESENT_ENUM,
            ZCL_TUYA_GAS_CLEAR_ENUM,
        ),
        (
            "_TZE204_yojqa8xn",
            "TS0601",
            ZCL_TUYA_GAS_PRESENT_ENUM,
            ZCL_TUYA_GAS_CLEAR_ENUM,
        ),
        (
            "_TZE200_ggev5fsl",
            "TS0601",
            ZCL_TUYA_GAS_PRESENT_ENUM,
            ZCL_TUYA_GAS_CLEAR_ENUM,
        ),
        (
            "_TZE200_u319yc66",
            "TS0601",
            ZCL_TUYA_GAS_PRESENT_ENUM,
            ZCL_TUYA_GAS_CLEAR_ENUM,
        ),
        (
            "_TZE200_kvpwq8z7",
            "TS0601",
            ZCL_TUYA_GAS_PRESENT_ENUM,
            ZCL_TUYA_GAS_CLEAR_ENUM,
        ),
    ],
)
async def test_tuya_gas_quirk(
    zigpy_device_from_v2_quirk, model, manuf, gas_present, gas_clear
):
    """Test Tuya Gas Quirks using IAS cluster."""
    quirked_device = zigpy_device_from_v2_quirk(model, manuf)
    ep = quirked_device.endpoints[1]

    assert ep.tuya_manufacturer is not None
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)

    assert ep.ias_zone is not None
    assert isinstance(ep.ias_zone, IasZone)

    ias_listener = ClusterListener(ep.ias_zone)
    zcl_ias_id = IasZone.AttributeDefs.zone_status.id

    hdr, data = ep.tuya_manufacturer.deserialize(gas_present)
    status = ep.tuya_manufacturer.handle_get_data(data.data)

    assert status == foundation.Status.SUCCESS

    assert len(ias_listener.attribute_updates) == 1
    assert ias_listener.attribute_updates[0][0] == zcl_ias_id
    assert ias_listener.attribute_updates[0][1] == IasZone.ZoneStatus.Alarm_1

    hdr, data = ep.tuya_manufacturer.deserialize(gas_clear)
    status = ep.tuya_manufacturer.handle_get_data(data.data)

    assert len(ias_listener.attribute_updates) == 2
    assert ias_listener.attribute_updates[1][0] == zcl_ias_id
    assert ias_listener.attribute_updates[1][1] == 0
