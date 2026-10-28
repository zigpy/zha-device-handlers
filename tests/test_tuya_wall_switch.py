"""Tests for Tuya wall switch v2 quirks (TS0001-TS0004, TS000F, TS0011-TS0013)."""

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.profiles import zha
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import OnOff

import zhaquirks
from zhaquirks.tuya import (
    ExternalSwitchType,
    TuyaZBExternalSwitchTypeCluster,
    TuyaZBOnOffAttributeCluster,
)
from zhaquirks.tuya.tuya_wall_switch import EnchantedSwitchDevice

zhaquirks.setup()


EXT_CLUSTER_ID = TuyaZBExternalSwitchTypeCluster.cluster_id


def _quirk_definition(manufacturer: str, model: str):
    """Return the quirk definition the registry resolves this device to."""
    for entry in DEVICE_REGISTRY:
        if (manufacturer, model) in entry.device_match.applies_to:
            return entry.zha_device_factory.quirk_definition
    pytest.fail(f"no v2 quirk registered for {manufacturer} {model}")


@pytest.mark.parametrize(
    "manufacturer,model,num_endpoints",
    [
        # With neutral (TS0001-TS0004)
        ("_TZ3000_xkap8wtb", "TS0001", 1),
        ("_TZ3000_aaifmpuq", "TS0002", 2),
        ("_TZ3000_pf7swkqp", "TS0003", 3),
        ("_TZ3000_ltt60asa", "TS0004", 4),
        # With neutral, with metering (TS000F)
        ("_TZ3000_dlhhrhs8", "TS000F", 1),
        ("_TZ3000_m8f3z8ju", "TS000F", 2),
        # No neutral (TS0011-TS0013)
        ("_TZ3000_ji4araar", "TS0011", 1),
        ("_TZ3000_4zf0crgo", "TS0012", 2),
        ("_TZ3000_avotanj3", "TS0013", 3),
    ],
)
def test_v2_quirk_exposes_external_switch_type(
    zigpy_device_from_v2_quirk, manufacturer, model, num_endpoints
):
    """V2 quirk types the device as ON_OFF_SWITCH and exposes selects on endpoint 1."""
    cluster_ids = {
        ep: {OnOff.cluster_id: ClusterType.Server} for ep in range(1, num_endpoints + 1)
    }
    cluster_ids[1][EXT_CLUSTER_ID] = ClusterType.Server
    device = zigpy_device_from_v2_quirk(
        manufacturer,
        model,
        endpoint_ids=list(range(1, num_endpoints + 1)),
        cluster_ids=cluster_ids,
    )

    assert isinstance(device, EnchantedSwitchDevice)

    for ep_id in range(1, num_endpoints + 1):
        assert device.endpoints[ep_id].device_type == zha.DeviceType.ON_OFF_SWITCH

    cluster = device.endpoints[1].in_clusters[EXT_CLUSTER_ID]
    assert isinstance(cluster, TuyaZBExternalSwitchTypeCluster)

    definition = _quirk_definition(manufacturer, model)
    by_attr = {
        m.attribute_name: m
        for m in definition.entity_metadata
        if getattr(m, "attribute_name", None) is not None
    }
    for attr in ("indicator_mode", "power_on_state", "external_switch_type"):
        assert attr in by_attr, f"missing {attr}"
        assert by_attr[attr].endpoint_id == 1
    assert by_attr["external_switch_type"].enum is ExternalSwitchType
    assert by_attr["indicator_mode"].unique_id_suffix == "6-indicator_mode"
    assert by_attr["power_on_state"].unique_id_suffix == "6-power_on_state"


def test_external_switch_type_enum_values():
    """The enum exposes the three states documented by Tuya."""
    names = {member.name for member in ExternalSwitchType}
    assert names == {"Toggle", "State", "Momentary"}


def test_indicator_mode_alias_shares_attribute_id():
    """backlight_mode alias and indicator_mode point to the same wire attribute."""
    attrs = TuyaZBOnOffAttributeCluster.AttributeDefs
    assert attrs.backlight_mode.id == attrs.indicator_mode.id == 0x8001
