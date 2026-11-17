"""Tests for Busch-Jaeger ZigBee Light Link wall transmitter quirks."""

import pytest
from zha.quirks import QUIRK_REGISTRY_ENTRY_ATTR
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import LevelControl, OnOff

import zhaquirks

zhaquirks.setup()

ROW_ENDPOINTS = {1: 0x0A, 2: 0x0B, 3: 0x0C, 4: 0x0D}


def _rocker_clusters() -> dict:
    """OnOff + LevelControl as output (client) clusters on each rocker endpoint."""
    return {
        endpoint: {
            OnOff.cluster_id: ClusterType.Client,
            LevelControl.cluster_id: ClusterType.Client,
        }
        for endpoint in ROW_ENDPOINTS.values()
    }


def _triggers(device) -> dict:
    """Return the device automation triggers of the applied quirk."""
    entry = getattr(device, QUIRK_REGISTRY_ENTRY_ATTR)
    return entry.zha_device_factory.quirk_definition.device_automation_triggers


@pytest.mark.parametrize("model", ["RM01", "RB01"])
def test_quirk_applies(zigpy_device_from_v2_quirk, model):
    """The quirk applies to both Busch-Jaeger models."""
    device = zigpy_device_from_v2_quirk(
        "Busch-Jaeger", model, cluster_ids=_rocker_clusters()
    )
    assert getattr(device, QUIRK_REGISTRY_ENTRY_ATTR, None) is not None


@pytest.mark.parametrize("model", ["RM01", "RB01"])
def test_device_automation_triggers(zigpy_device_from_v2_quirk, model):
    """Every rocker row exposes on/off and dim triggers on its own endpoint."""
    device = zigpy_device_from_v2_quirk(
        "Busch-Jaeger", model, cluster_ids=_rocker_clusters()
    )
    triggers = _triggers(device)

    for row, endpoint in ROW_ENDPOINTS.items():
        assert dict(triggers[("remote_button_short_press", f"on_row_{row}")]) == {
            "endpoint_id": endpoint,
            "cluster_id": OnOff.cluster_id,
            "command": "on",
        }
        assert dict(triggers[("remote_button_short_press", f"off_row_{row}")]) == {
            "endpoint_id": endpoint,
            "cluster_id": OnOff.cluster_id,
            "command": "off",
        }
        assert dict(triggers[("remote_button_long_press", f"up_row_{row}")]) == {
            "endpoint_id": endpoint,
            "cluster_id": LevelControl.cluster_id,
            "command": "step_with_on_off",
        }
        assert dict(triggers[("remote_button_long_press", f"down_row_{row}")]) == {
            "endpoint_id": endpoint,
            "cluster_id": LevelControl.cluster_id,
            "command": "step",
        }
        assert dict(triggers[("remote_button_long_release", f"stop_row_{row}")]) == {
            "endpoint_id": endpoint,
            "cluster_id": LevelControl.cluster_id,
            "command": "stop",
        }
