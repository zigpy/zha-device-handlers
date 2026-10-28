"""Tests for Namron quirks."""

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl.clusters.general import LevelControl

import zhaquirks

zhaquirks.setup()


@pytest.mark.parametrize("model", ["4512772", "4512773"])
def test_remote_4512772_triggers(zigpy_device_from_v2_quirk, model):
    """Both color variants get the same 24 device automation triggers."""
    device = zigpy_device_from_v2_quirk("NAMRON AS", model)

    entry = DEVICE_REGISTRY.match_entry(device)
    triggers = entry.zha_device_factory.quirk_definition.device_automation_triggers
    assert len(triggers) == 24
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
    # button_2 is the off-side sibling of button_1 on the same channel;
    # Stop carries no direction, so it gets an identical release trigger.
    assert (
        triggers[("remote_button_long_release", "button_2")]
        == triggers[("remote_button_long_release", "button_1")]
    )
    # endpoint 1 is physically the rightmost channel (button 7/8), endpoint 4
    # the leftmost (button 1/2) - regression guard for that mapping.
    assert triggers[("remote_button_short_press", "button_1")]["endpoint_id"] == 4
    assert triggers[("remote_button_short_press", "button_7")]["endpoint_id"] == 1
