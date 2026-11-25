"""Tests for Tuya gas quirks."""

import pytest
from zha.application.platforms.binary_sensor import DeviceValueBinarySensor
from zha.quirks import DEVICE_REGISTRY
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.security import IasZone

from tests.common import ClusterListener, attribute_cache_row
import zhaquirks
from zhaquirks.builder import BinarySensorDeviceClass, EntityType
import zhaquirks.tuya
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.mcu import TuyaMCUCluster
from zhaquirks.tuya.tuya_gas import LIFECYCLE

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


@pytest.mark.parametrize(
    "frame,lifecycle,problem",
    [
        (ZCL_TUYA_GAS_LIFECYCLE_OK, True, False),
        (ZCL_TUYA_GAS_LIFECYCLE_END, False, True),
    ],
)
async def test_nous_e9_lifecycle_inverted(
    zigpy_device_from_v2_quirk, frame, lifecycle, problem
):
    """NOUS E9 DP 12 is True while healthy; the PROBLEM entity shows the inverse."""
    quirked_device = zigpy_device_from_v2_quirk("_TZE204_qvxrkeif", "TS0601")
    tuya_cluster = quirked_device.endpoints[1].tuya_manufacturer

    hdr, data = tuya_cluster.deserialize(frame)
    status = tuya_cluster.handle_get_data(data.data)
    assert status == foundation.Status.SUCCESS

    # The device value keeps the device's own value, not an attribute
    assert "lifecycle" not in tuya_cluster.attributes_by_name
    assert quirked_device.store[LIFECYCLE] is lifecycle

    entry = DEVICE_REGISTRY.match_entry(quirked_device)
    entities = {
        added.kwargs["unique_id_suffix"]: added
        for added in entry.zha_device_factory.quirk_definition.added_entities
    }
    assert entities["1-lifecycle"].entity_cls is DeviceValueBinarySensor
    converter = entities["1-lifecycle"].kwargs["value_converter"]
    assert converter(quirked_device.store[LIFECYCLE]) is problem


def test_nous_e9_device_values(zigpy_device_from_v2_quirk):
    """NOUS E9 keeps its binary sensors as device values with unchanged entities."""
    quirked_device = zigpy_device_from_v2_quirk("_TZE204_qvxrkeif", "TS0601")
    definition = DEVICE_REGISTRY.match_entry(
        quirked_device
    ).zha_device_factory.quirk_definition

    assert [
        m.attribute_name
        for m in definition.entity_metadata
        if m.cluster_id == TUYA_CLUSTER_ID
    ] == []
    assert {
        (
            added.entity_cls,
            added.kwargs["unique_id_suffix"],
            added.kwargs["entity_type"],
            added.kwargs["device_class"],
            added.kwargs["translation_key"],
        )
        for added in definition.added_entities
    } == {
        (
            DeviceValueBinarySensor,
            "1-preheat",
            EntityType.DIAGNOSTIC,
            None,
            "preheat",
        ),
        (
            DeviceValueBinarySensor,
            "1-fault_alarm",
            EntityType.DIAGNOSTIC,
            BinarySensorDeviceClass.PROBLEM,
            "fault_alarm",
        ),
        (
            DeviceValueBinarySensor,
            "1-lifecycle",
            EntityType.DIAGNOSTIC,
            BinarySensorDeviceClass.PROBLEM,
            "lifecycle",
        ),
    }


@pytest.mark.parametrize("typed", [True, False])
def test_nous_e9_attributes_migrated(zigpy_device_from_v2_quirk, typed):
    """NOUS E9's old attributes move into its device values, read as before."""
    quirked_device = zigpy_device_from_v2_quirk("_TZE204_qvxrkeif", "TS0601")
    values = quirked_device.store.namespace(LIFECYCLE.namespace)

    # The invented attributes the quirk had: ID and value
    old_attributes = {
        "preheat": (0xEF0A, t.Bool.false),
        "fault_alarm": (0xEF0B, t.Bool.true),
        "lifecycle": (0xEF0C, t.Bool.false),
    }
    rows = [
        attribute_cache_row(
            quirked_device,
            TUYA_CLUSTER_ID,
            attr_id,
            value.serialize() if typed else int(value),
            foundation.DataTypeId.bool_ if typed else None,
            manufacturer_code=quirked_device.manufacturer_id,
        )
        for attr_id, value in old_attributes.values()
    ]

    result = quirked_device.load_attribute_cache(rows, migrate=True)
    assert len(result.migrated) == len(rows)

    assert {key: values[key] for key in old_attributes} == {
        "preheat": 0,
        "fault_alarm": 1,
        "lifecycle": 0,
    }
    # A sensor at the end of its service life is still shown as a problem
    assert quirked_device.store[LIFECYCLE] is False
