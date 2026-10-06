"""Tests for Develco smart button."""

from zha.quirks import DEVICE_REGISTRY as ZHA_DEVICE_REGISTRY
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import BinaryInput, OnOff

import zhaquirks
from zhaquirks.builder import EntityType
from zhaquirks.develco.smart_button import CustomOnOff

zhaquirks.setup()


async def test_sbtzb110_quirk_metadata(zigpy_device_from_v2_quirk):
    """Test the smart button quirk exposes the expected v2 entity metadata."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "SBTZB-110",
        endpoint_ids=[32],
        cluster_ids={
            32: {
                OnOff.cluster_id: ClusterType.Client,
                BinaryInput.cluster_id: ClusterType.Server,
            }
        },
    )
    entry = ZHA_DEVICE_REGISTRY.match_entry(device)
    assert entry is not None

    manufacturer_models = {
        (m.manufacturer, m.model) for m in entry.device_match.applies_to
    }
    assert ("frient A/S", "SBTZB-110") in manufacturer_models
    assert ("Develco Products A/S", "SBTZB-110") in manufacturer_models

    entity_map = {
        m.translation_key: m
        for m in entry.zha_device_factory.quirk_definition.entity_metadata
        if m.translation_key is not None
    }

    assert entity_map["button_press_action_delay"].fallback_name == (
        "Button press action delay"
    )
    assert entity_map["button_press_blink_led"].entity_type is EntityType.CONFIG


def test_sbtzb110_custom_onoff_cluster_metadata():
    """Test the custom OnOff cluster keeps the expected manufacturer attributes."""
    assert CustomOnOff.cluster_id == OnOff.cluster_id
    assert (
        CustomOnOff.AttributeDefs.button_press_action_delay.manufacturer_code == 0x1015
    )
    assert CustomOnOff.AttributeDefs.button_press_blink_led.manufacturer_code == 0x1015
