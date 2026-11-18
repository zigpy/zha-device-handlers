"""Tests for Nimly lock quirks."""

import pytest
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.closures import DoorLock
from zigpy.zcl.clusters.general import PowerConfiguration

import zhaquirks
from zhaquirks import DoublingPowerConfigurationCluster
from zhaquirks.nimly import NIMLY
from zhaquirks.nimly.lock import (
    NimlyDoorLock,
    last_action_converter,
    last_action_source_converter,
    last_action_user_converter,
)

zhaquirks.setup()


def test_last_action_source_converter() -> None:
    """Test the last action source converter for Nimly Door Lock cluster."""
    assert last_action_source_converter(0x00020001) == "zigbee", (
        "Expected 'zigbee' for value 0x00010001"
    )
    assert last_action_source_converter(0x03010001) == "fingerprint", (
        "Expected 'fingerprint' for value 0x03010001"
    )
    assert last_action_source_converter(0x99010001) is None, (
        "Expected None for value 0x99010001"
    )


def test_last_action_converter() -> None:
    """Test the last action converter for Nimly Door Lock cluster."""
    assert last_action_converter(0x0A010001) == "lock", (
        "Expected 'lock' for value 0x0a010001"
    )
    assert last_action_converter(0x00020001) == "unlock", (
        "Expected 'unlock' for value 0x00020001"
    )
    assert last_action_converter(0x01030001) is None, (
        "Expected None for value 0x01030001"
    )


def test_last_action_user_converter() -> None:
    """Test the last action user converter for Nimly Door Lock cluster."""
    assert last_action_user_converter(0x01020001) == 1, (
        "Expected user ID 1 for value 0x01020001"
    )
    assert last_action_user_converter(0x02020010) == 16, (
        "Expected user ID 16 for value 0x02020010"
    )


@pytest.mark.parametrize("model", ["EasyCodeTouch", "easyCodeTouch_v1"])
def test_easyfingertouch_battery_doubled(zigpy_device_from_v2_quirk, model) -> None:
    """Test EasyFingerTouch locks report 0-100 battery and get doubled to 0-200."""
    device = zigpy_device_from_v2_quirk(
        NIMLY,
        model,
        endpoint_ids=[11],
        cluster_ids={
            11: {
                PowerConfiguration.cluster_id: ClusterType.Server,
                DoorLock.cluster_id: ClusterType.Server,
            }
        },
    )
    power = device.endpoints[11].power
    assert isinstance(power, DoublingPowerConfigurationCluster)
    assert isinstance(device.endpoints[11].door_lock, NimlyDoorLock)

    power.update_attribute(
        PowerConfiguration.AttributeDefs.battery_percentage_remaining.id, 82
    )
    assert (
        power.get(PowerConfiguration.AttributeDefs.battery_percentage_remaining.name)
        == 164
    )
