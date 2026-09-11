"""Tests for Namron quirks."""

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import LevelControl, Ota, PowerConfiguration

import zhaquirks
from zhaquirks.builder.metadata import PreventDefaultEntityCreationMetadata

zhaquirks.setup()


@pytest.mark.parametrize("model", ["4512772", "4512773"])
def test_remote_4512772_triggers(zigpy_device_from_v2_quirk, model):
    """Both color variants get the same 20 device automation triggers."""
    device = zigpy_device_from_v2_quirk("NAMRON AS", model)

    entry = DEVICE_REGISTRY.match_entry(device)
    triggers = entry.zha_device_factory.quirk_definition.device_automation_triggers
    assert len(triggers) == 20
    assert triggers[("remote_button_short_press", "button_1")]["command"] == "on"
    assert triggers[("remote_button_short_press", "button_2")]["command"] == "off"
    assert triggers[("remote_button_long_press", "button_1")]["params"] == {
        "move_mode": LevelControl.MoveMode.Up
    }
    assert triggers[("remote_button_long_press", "button_2")]["params"] == {
        "move_mode": LevelControl.MoveMode.Down
    }
    assert (
        triggers[("remote_button_long_release", "button_1")]["command"]
        == "stop_with_on_off"
    )
    # endpoint 1 is physically the rightmost channel (button 7/8), endpoint 4
    # the leftmost (button 1/2) - regression guard for that mapping.
    assert triggers[("remote_button_short_press", "button_1")]["endpoint_id"] == 4
    assert triggers[("remote_button_short_press", "button_7")]["endpoint_id"] == 1


def test_remote_4512772_hides_duplicate_battery_and_firmware(
    zigpy_device_from_v2_quirk,
):
    """Only endpoint 1 keeps its battery/firmware entities; 2-4 are duplicates."""
    device = zigpy_device_from_v2_quirk("NAMRON AS", "4512772")
    entry = DEVICE_REGISTRY.match_entry(device)
    disabled = entry.zha_device_factory.quirk_definition.disabled_default_entities

    assert set(disabled) == {
        PreventDefaultEntityCreationMetadata(
            endpoint_id=ep,
            cluster_id=cluster_id,
            cluster_type=cluster_type,
            unique_id_suffix=None,
            function=None,
        )
        for ep in (2, 3, 4)
        for cluster_id, cluster_type in (
            (PowerConfiguration.cluster_id, ClusterType.Server),
            (Ota.cluster_id, ClusterType.Client),
        )
    }
    assert all(m.endpoint_id != 1 for m in disabled)
