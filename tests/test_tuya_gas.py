"""Tests for Tuya gas quirks."""

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import foundation
from zigpy.zcl.clusters.security import IasZone

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.const import BatterySize
import zhaquirks.tuya
from zhaquirks.tuya.mcu import TuyaMCUCluster
from zhaquirks.tuya.tuya_gas import TuyaSelfTestResult

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
            "_TZE204_qvxrkeif",
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
        (
            "_TZE204_uo8qcagc",
            "TS0601",
            ZCL_TUYA_GAS_PRESENT_ENUM,
            ZCL_TUYA_GAS_CLEAR_ENUM,
        ),
        (
            "_TZE284_sonkaxrd",
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


# DP 12, bool: True while the sensor is healthy, False at end of life
ZCL_TUYA_GAS_LIFECYCLE_OK = b"\tL\x01\x00\x05\x0c\x01\x00\x01\x01"
ZCL_TUYA_GAS_LIFECYCLE_END = b"\tL\x01\x00\x05\x0c\x01\x00\x01\x00"


@pytest.mark.parametrize("manuf", ["_TZE204_qvxrkeif", "_TZE284_sonkaxrd"])
@pytest.mark.parametrize(
    "frame,lifecycle,problem",
    [
        (ZCL_TUYA_GAS_LIFECYCLE_OK, True, False),
        (ZCL_TUYA_GAS_LIFECYCLE_END, False, True),
    ],
)
async def test_nous_e9_lifecycle_inverted(
    zigpy_device_from_v2_quirk, manuf, frame, lifecycle, problem
):
    """NOUS E9/E12 DP 12 is True while healthy; PROBLEM entity shows inverse."""
    quirked_device = zigpy_device_from_v2_quirk(manuf, "TS0601")
    tuya_cluster = quirked_device.endpoints[1].tuya_manufacturer

    hdr, data = tuya_cluster.deserialize(frame)
    status = tuya_cluster.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    # The attribute keeps the device's own value.
    assert tuya_cluster.get("lifecycle") == lifecycle

    entry = DEVICE_REGISTRY.match_entry(quirked_device)
    entities = {
        metadata.resolved_unique_id_suffix: metadata
        for metadata in entry.zha_device_factory.quirk_definition.entity_metadata
    }
    converter = entities["lifecycle"].attribute_converter
    assert converter(tuya_cluster.get("lifecycle")) is problem
    # After a restart the attribute cache holds a plain int.
    assert converter(int(lifecycle)) is problem


async def test_nous_e12_co_sensor(zigpy_device_from_v2_quirk):
    """Test NOUS E12 CO concentration, diagnostic, and battery DPs."""
    quirked_device = zigpy_device_from_v2_quirk("_TZE284_sonkaxrd", "TS0601")
    ep = quirked_device.endpoints[1]
    tuya_cluster = ep.tuya_manufacturer

    # DP 2, value 35 ppm: 0x00000023
    co_frame = b"\tL\x01\x00\x05\x02\x02\x00\x04\x00\x00\x00\x23"
    hdr, data = tuya_cluster.deserialize(co_frame)
    assert tuya_cluster.handle_get_data(data.data) == foundation.Status.SUCCESS
    assert tuya_cluster.get("co") == 35

    # DP 8, bool True (self_checking)
    chk_frame = b"\tL\x01\x00\x06\x08\x01\x00\x01\x01"
    hdr, data = tuya_cluster.deserialize(chk_frame)
    assert tuya_cluster.handle_get_data(data.data) == foundation.Status.SUCCESS
    assert tuya_cluster.get("self_checking") == 1

    # DP 9, enum 1 (Success)
    res_frame = b"\tL\x01\x00\x07\x09\x04\x00\x01\x01"
    hdr, data = tuya_cluster.deserialize(res_frame)
    assert tuya_cluster.handle_get_data(data.data) == foundation.Status.SUCCESS
    assert tuya_cluster.get("self_test_result") == TuyaSelfTestResult.Success

    # DP 10, bool True (preheat) & DP 11, bool True (fault_alarm)
    pre_frame = b"\tL\x01\x00\x08\x0a\x01\x00\x01\x01"
    hdr, data = tuya_cluster.deserialize(pre_frame)
    assert tuya_cluster.handle_get_data(data.data) == foundation.Status.SUCCESS
    assert tuya_cluster.get("preheat") == 1

    flt_frame = b"\tL\x01\x00\x09\x0b\x01\x00\x01\x01"
    hdr, data = tuya_cluster.deserialize(flt_frame)
    assert tuya_cluster.handle_get_data(data.data) == foundation.Status.SUCCESS
    assert tuya_cluster.get("fault_alarm") == 1

    # DP 14, enum 2 (High) -> 200 (100% battery remaining), 1 x CR123A
    bat_frame = b"\tL\x01\x00\x0a\x0e\x04\x00\x01\x02"
    hdr, data = tuya_cluster.deserialize(bat_frame)
    assert tuya_cluster.handle_get_data(data.data) == foundation.Status.SUCCESS
    assert ep.power.get("battery_percentage_remaining") == 200
    assert ep.power.get("battery_size") == BatterySize.CR123A
