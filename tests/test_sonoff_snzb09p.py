"""Tests for the SONOFF SNZB-09P quirk."""

from unittest.mock import AsyncMock

import pytest
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import PowerConfiguration

from zhaquirks.sonoff.snzb09p import (
    ALARM_STATE_MANUAL,
    ALARM_STATE_OFF,
    ALARM_STATE_SCENE,
    ATTR_SONOFF_ALARM_ACTIVE,
    CMD_SOUND_AND_LIGHT_ALARM_SETTINGS,
    SONOFF_CLUSTER_FC11_ID,
    SONOFF_MANUFACTURER_CODE,
    SONOFF_SNZB09P,
    SUBCMD_START_MANUAL_ALARM,
    SUBCMD_STOP_ALARM,
    AlarmSoundType,
    SonoffSNZB09PFC11Cluster,
)


def test_alarm_sound_type_values() -> None:
    """Test that the sound type values match the current firmware mapping."""
    assert {member.name: int(member) for member in AlarmSoundType} == {
        "Classic_Siren": 0x00,
        "Steady_Siren": 0x01,
        "Rising_Siren": 0x03,
        "Warning_Siren": 0x05,
        "Rapid_Siren": 0x06,
        "Emergency_Siren": 0x08,
        "Chirp_Tone": 0x02,
        "Hi_Lo_Tone": 0x04,
        "Intermittent_Tone": 0x07,
        "Pulse_Tone": 0x09,
        "Chime_Doorbell": 0x0A,
        "Chime_Classic_Clock": 0x0B,
        "Chime_Electronic_Clock": 0x0C,
        "Chime_Bright": 0x0D,
        "Chime_Soft": 0x0E,
    }
    assert {int(member) for member in AlarmSoundType} == set(range(0x0F))

    sound_type_metadata = next(
        metadata
        for metadata in SONOFF_SNZB09P.zha_device_factory.quirk_definition.entity_metadata
        if metadata.attribute_name == "alarm_sound_type"
    )
    assert sound_type_metadata.enum is AlarmSoundType


def _create_device(zigpy_device_from_v2_quirk):
    """Create an SNZB-09P with the clusters replaced by this quirk."""
    return zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="SNZB-09P",
        cluster_ids={
            1: {
                PowerConfiguration.cluster_id: ClusterType.Server,
                SONOFF_CLUSTER_FC11_ID: ClusterType.Server,
            }
        },
    )


@pytest.mark.parametrize(
    ("enabled", "expected_subcommand"),
    (
        (True, SUBCMD_START_MANUAL_ALARM),
        (False, SUBCMD_STOP_ALARM),
    ),
)
async def test_alarm_active_write(
    zigpy_device_from_v2_quirk, enabled, expected_subcommand
) -> None:
    """Test mapping the virtual alarm switch to the firmware command."""
    device = _create_device(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[1].sonoff_manufacturer
    assert isinstance(cluster, SonoffSNZB09PFC11Cluster)
    cluster.command = AsyncMock()

    (records,) = await cluster.write_attributes({"alarm_active": enabled})

    cluster.command.assert_awaited_once_with(
        CMD_SOUND_AND_LIGHT_ALARM_SETTINGS,
        expected_subcommand,
        manufacturer=SONOFF_MANUFACTURER_CODE,
    )
    assert records[0].status is foundation.Status.SUCCESS
    assert bool(cluster.get(ATTR_SONOFF_ALARM_ACTIVE)) is enabled


@pytest.mark.parametrize(
    ("alarm_state", "expected_active"),
    (
        (ALARM_STATE_OFF, False),
        (ALARM_STATE_MANUAL, True),
        (ALARM_STATE_SCENE, True),
    ),
)
def test_alarm_state_report(
    zigpy_device_from_v2_quirk, alarm_state, expected_active
) -> None:
    """Test syncing the virtual switch from the firmware state report."""
    device = _create_device(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[1].sonoff_manufacturer

    cluster.deserialize(
        bytes(
            (
                0x1D,
                SONOFF_MANUFACTURER_CODE & 0xFF,
                SONOFF_MANUFACTURER_CODE >> 8,
                0x01,
                CMD_SOUND_AND_LIGHT_ALARM_SETTINGS,
                0x04,
                alarm_state,
            )
        )
    )

    assert bool(cluster.get(ATTR_SONOFF_ALARM_ACTIVE)) is expected_active
