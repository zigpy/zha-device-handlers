"""Tests for Tuya TS011F plugs."""

import pytest
from zha.application import EntityType
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import OnOff

from zhaquirks.tuya.ts011f_plug import PowerOnState, SwitchBackLight


@pytest.mark.parametrize(
    "manufacturer,model",
    [
        ("_TZ3000_5f43h46b", "TS011F"),
        ("_TZ3000_okaz9tjs", "TS011F"),
    ],
)
async def test_ts011f_v2_quirk(zigpy_device_from_v2_quirk, manufacturer, model):
    """Test TS011F V2 quirk."""
    device = zigpy_device_from_v2_quirk(manufacturer, model)

    entry = DEVICE_REGISTRY.match_entry(device)
    assert entry is not None

    definition = entry.zha_device_factory.quirk_definition

    assert len(definition.entity_metadata) == 3

    metadata_by_attribute = {
        metadata.attribute_name: metadata for metadata in definition.entity_metadata
    }

    child_lock = metadata_by_attribute["child_lock"]
    assert child_lock.cluster_id == OnOff.cluster_id
    assert child_lock.cluster_type is ClusterType.Server
    assert child_lock.entity_type is EntityType.CONFIG
    assert child_lock.translation_key == "child_lock"
    assert child_lock.fallback_name == "Child lock"
    assert child_lock.resolved_unique_id_suffix == "6-child_lock"

    power_on_state = metadata_by_attribute["power_on_state"]
    assert power_on_state.cluster_id == OnOff.cluster_id
    assert power_on_state.cluster_type is ClusterType.Server
    assert power_on_state.entity_type is EntityType.CONFIG
    assert power_on_state.translation_key == "power_on_state"
    assert power_on_state.fallback_name == "Power on state"
    assert power_on_state.enum is PowerOnState

    backlight_mode = metadata_by_attribute["backlight_mode"]
    assert backlight_mode.cluster_id == OnOff.cluster_id
    assert backlight_mode.cluster_type is ClusterType.Server
    assert backlight_mode.entity_type is EntityType.CONFIG
    assert backlight_mode.translation_key == "backlight_mode"
    assert backlight_mode.fallback_name == "Backlight mode"
    assert backlight_mode.enum is SwitchBackLight
