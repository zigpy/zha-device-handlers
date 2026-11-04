"""Tests for the SONOFF SNZB-09P quirk."""

from unittest.mock import AsyncMock

import pytest
from zha.quirks import QUIRK_REGISTRY_ENTRY_ATTR
from zigpy.exceptions import DeliveryError
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import PowerConfiguration

from zhaquirks.sonoff.snzb09p import (
    ALARM_STATE_MANUAL,
    ALARM_STATE_OFF,
    ALARM_STATE_SCENE,
    ATTR_SONOFF_ALARM_ACTIVE,
    ATTR_SONOFF_ALARM_DURATION,
    ATTR_SONOFF_ALARM_VOLUME_LEVEL,
    ATTR_SONOFF_POWER_SUPPLY_MODE,
    BATTERY_PERCENTAGE_FULL,
    BATTERY_PERCENTAGE_UNKNOWN,
    CMD_SOUND_AND_LIGHT_ALARM_SETTINGS,
    SONOFF_CLUSTER_FC11_ID,
    SONOFF_MANUFACTURER_CODE,
    SONOFF_SNZB09P,
    SONOFF_SNZB09P_CHIME,
    SUBCMD_START_MANUAL_ALARM,
    SUBCMD_STOP_ALARM,
    AlarmSoundType,
    BaseAlarmSoundType,
    PowerSupplyMode,
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


def _create_device(zigpy_device_from_v2_quirk, firmware_version=None):
    """Create an SNZB-09P with the clusters replaced by this quirk."""
    return zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="SNZB-09P",
        firmware_version=firmware_version,
        cluster_ids={
            1: {
                PowerConfiguration.cluster_id: ClusterType.Server,
                SONOFF_CLUSTER_FC11_ID: ClusterType.Server,
            }
        },
    )


@pytest.mark.parametrize(
    ("firmware_version", "expected_enum", "expected_count"),
    (
        (None, BaseAlarmSoundType, 10),
        (0x00001104, BaseAlarmSoundType, 10),
        (0x00001105, BaseAlarmSoundType, 10),
        (0x00001106, BaseAlarmSoundType, 10),
        (0x00001107, BaseAlarmSoundType, 10),
        (0x00001108, BaseAlarmSoundType, 10),
        (0x00001109, AlarmSoundType, 15),
        (0x00001200, AlarmSoundType, 15),
    ),
)
def test_firmware_sound_options(
    zigpy_device_from_v2_quirk, firmware_version, expected_enum, expected_count
) -> None:
    """Select exactly one quirk and expose only the supported sound options."""
    device = _create_device(zigpy_device_from_v2_quirk, firmware_version)
    matches = [
        entry
        for entry in (SONOFF_SNZB09P, SONOFF_SNZB09P_CHIME)
        if entry.device_match.matches(device)
    ]
    assert len(matches) == 1
    assert getattr(device, QUIRK_REGISTRY_ENTRY_ATTR) is matches[0]
    metadata = matches[0].zha_device_factory.quirk_definition.entity_metadata
    sound_entities = [m for m in metadata if m.attribute_name == "alarm_sound_type"]
    assert len(sound_entities) == 1
    assert sound_entities[0].enum is expected_enum
    assert {int(member) for member in sound_entities[0].enum} == set(
        range(expected_count)
    )
    assert {member.name: int(member) for member in BaseAlarmSoundType} == {
        member.name: int(member) for member in AlarmSoundType if int(member) < 0x0A
    }


def test_firmware_variants_preserve_entity_metadata() -> None:
    """Keep entity identities and other controls unchanged across firmware variants."""
    old = SONOFF_SNZB09P.zha_device_factory.quirk_definition
    new = SONOFF_SNZB09P_CHIME.zha_device_factory.quirk_definition
    assert old.entity_metadata[:-1] == new.entity_metadata[:-1]
    old_sound, new_sound = old.entity_metadata[-1], new.entity_metadata[-1]
    for field in (
        "attribute_name",
        "endpoint_id",
        "cluster_id",
        "unique_id_suffix",
        "translation_key",
        "fallback_name",
    ):
        assert getattr(old_sound, field) == getattr(new_sound, field)


@pytest.mark.parametrize("firmware_version", (None, 0x00001104, 0x00001109))
@pytest.mark.parametrize(
    ("enabled", "expected_subcommand"),
    (
        (True, SUBCMD_START_MANUAL_ALARM),
        (False, SUBCMD_STOP_ALARM),
    ),
)
async def test_alarm_active_write(
    zigpy_device_from_v2_quirk, firmware_version, enabled, expected_subcommand
) -> None:
    """Test mapping the virtual alarm switch to the firmware command."""
    device = _create_device(zigpy_device_from_v2_quirk, firmware_version)
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


@pytest.mark.parametrize("firmware_version", (None, 0x00001104, 0x00001109))
@pytest.mark.parametrize(
    ("alarm_state", "expected_active"),
    (
        (ALARM_STATE_OFF, False),
        (ALARM_STATE_MANUAL, True),
        (ALARM_STATE_SCENE, True),
    ),
)
def test_alarm_state_report(
    zigpy_device_from_v2_quirk, firmware_version, alarm_state, expected_active
) -> None:
    """Test syncing the virtual switch from the firmware state report."""
    device = _create_device(zigpy_device_from_v2_quirk, firmware_version)
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


@pytest.mark.parametrize("power_report_first", (False, True))
def test_battery_external_power_transitions(
    zigpy_device_from_v2_quirk, power_report_first
) -> None:
    """Mask battery readings on external power and restore them when unplugged."""
    device = _create_device(zigpy_device_from_v2_quirk)
    power = device.endpoints[1].power
    sonoff = device.endpoints[1].sonoff_manufacturer
    battery_attr = PowerConfiguration.AttributeDefs.battery_percentage_remaining.id

    if power_report_first:
        sonoff.update_attribute(ATTR_SONOFF_POWER_SUPPLY_MODE, PowerSupplyMode.ON)
        assert power.get(battery_attr) is None
    power.update_attribute(battery_attr, 120)
    if not power_report_first:
        assert power.get(battery_attr) == 120
        sonoff.update_attribute(ATTR_SONOFF_POWER_SUPPLY_MODE, PowerSupplyMode.ON)
    assert power.get(battery_attr) == BATTERY_PERCENTAGE_UNKNOWN

    # Keep receiving battery reports while plugged in, then restore the latest one.
    power.update_attribute(battery_attr, 100)
    assert power.get(battery_attr) == BATTERY_PERCENTAGE_UNKNOWN
    sonoff.update_attribute(ATTR_SONOFF_POWER_SUPPLY_MODE, PowerSupplyMode.OFF)
    assert power.get(battery_attr) == 100
    power.update_attribute(battery_attr, 90)
    assert power.get(battery_attr) == 90


def test_full_battery_on_external_power(zigpy_device_from_v2_quirk) -> None:
    """Show a fresh full-battery report, but do not reuse it after reconnecting."""
    device = _create_device(zigpy_device_from_v2_quirk)
    power = device.endpoints[1].power
    sonoff = device.endpoints[1].sonoff_manufacturer
    battery_attr = PowerConfiguration.AttributeDefs.battery_percentage_remaining.id

    power.update_attribute(battery_attr, BATTERY_PERCENTAGE_FULL)
    sonoff.update_attribute(ATTR_SONOFF_POWER_SUPPLY_MODE, PowerSupplyMode.ON)
    assert power.get(battery_attr) == BATTERY_PERCENTAGE_UNKNOWN

    power.update_attribute(battery_attr, BATTERY_PERCENTAGE_FULL)
    assert power.get(battery_attr) == BATTERY_PERCENTAGE_FULL
    sonoff.update_attribute(ATTR_SONOFF_POWER_SUPPLY_MODE, PowerSupplyMode.ON)
    assert power.get(battery_attr) == BATTERY_PERCENTAGE_FULL

    sonoff.update_attribute(ATTR_SONOFF_POWER_SUPPLY_MODE, PowerSupplyMode.OFF)
    assert power.get(battery_attr) == BATTERY_PERCENTAGE_FULL
    sonoff.update_attribute(ATTR_SONOFF_POWER_SUPPLY_MODE, PowerSupplyMode.ON)
    assert power.get(battery_attr) == BATTERY_PERCENTAGE_UNKNOWN

    power.update_attribute(battery_attr, BATTERY_PERCENTAGE_FULL)
    power.update_attribute(battery_attr, 180)
    assert power.get(battery_attr) == BATTERY_PERCENTAGE_UNKNOWN


def test_other_power_attributes_are_preserved(zigpy_device_from_v2_quirk) -> None:
    """External power must not mask unrelated battery attributes."""
    device = _create_device(zigpy_device_from_v2_quirk)
    power = device.endpoints[1].power
    device.endpoints[1].sonoff_manufacturer.update_attribute(
        ATTR_SONOFF_POWER_SUPPLY_MODE, PowerSupplyMode.ON
    )
    voltage_attr = PowerConfiguration.AttributeDefs.battery_voltage.id
    power.update_attribute(voltage_attr, 30)
    assert power.get(voltage_attr) == 30


@pytest.mark.parametrize("initial_active", (False, True))
@pytest.mark.parametrize("error", (TimeoutError, DeliveryError))
async def test_alarm_command_failure(
    zigpy_device_from_v2_quirk, initial_active, error
) -> None:
    """A failed start or stop must not falsely change the alarm state."""
    device = _create_device(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[1].sonoff_manufacturer
    cluster.update_attribute(ATTR_SONOFF_ALARM_ACTIVE, initial_active)
    cluster.command = AsyncMock(side_effect=error("Alarm command was not delivered"))

    (records,) = await cluster.write_attributes(
        {ATTR_SONOFF_ALARM_ACTIVE: not initial_active},
        manufacturer=SONOFF_MANUFACTURER_CODE,
    )

    assert records == [
        foundation.WriteAttributesStatusRecord(
            foundation.Status.FAILURE, ATTR_SONOFF_ALARM_ACTIVE
        )
    ]
    assert bool(cluster.get(ATTR_SONOFF_ALARM_ACTIVE)) is initial_active
    cluster.command.assert_awaited_once_with(
        CMD_SOUND_AND_LIGHT_ALARM_SETTINGS,
        SUBCMD_STOP_ALARM if initial_active else SUBCMD_START_MANUAL_ALARM,
        manufacturer=SONOFF_MANUFACTURER_CODE,
    )


@pytest.mark.parametrize("include_alarm", (False, True))
@pytest.mark.parametrize("volume_rejected", (False, True))
async def test_configuration_write(
    zigpy_device_from_v2_quirk, include_alarm, volume_rejected
) -> None:
    """Forward real settings and preserve each write result alongside alarm control."""
    device = _create_device(zigpy_device_from_v2_quirk)
    cluster = device.endpoints[1].sonoff_manufacturer
    cluster.update_attribute(ATTR_SONOFF_ALARM_VOLUME_LEVEL, 1)
    cluster.command = AsyncMock()
    volume_status = (
        foundation.Status.INVALID_VALUE
        if volume_rejected
        else foundation.Status.SUCCESS
    )
    cluster.write_attributes_raw = AsyncMock(
        return_value=[
            [
                foundation.WriteAttributesStatusRecord(
                    volume_status,
                    ATTR_SONOFF_ALARM_VOLUME_LEVEL if volume_rejected else None,
                )
            ]
        ]
    )
    attributes = {
        "alarm_volume_level": 2,
        ATTR_SONOFF_ALARM_DURATION: 10,
    }
    if include_alarm:
        attributes[ATTR_SONOFF_ALARM_ACTIVE] = True

    (records,) = await cluster.write_attributes(attributes)

    expected_statuses = {
        ATTR_SONOFF_ALARM_VOLUME_LEVEL: volume_status,
        ATTR_SONOFF_ALARM_DURATION: foundation.Status.SUCCESS,
    }
    if include_alarm:
        expected_statuses[ATTR_SONOFF_ALARM_ACTIVE] = foundation.Status.SUCCESS
        cluster.command.assert_awaited_once_with(
            CMD_SOUND_AND_LIGHT_ALARM_SETTINGS,
            SUBCMD_START_MANUAL_ALARM,
            manufacturer=SONOFF_MANUFACTURER_CODE,
        )
    else:
        cluster.command.assert_not_awaited()
    assert len(records) == len(expected_statuses)
    assert {record.attrid: record.status for record in records} == expected_statuses
    assert bool(cluster.get(ATTR_SONOFF_ALARM_ACTIVE)) is include_alarm
    assert cluster.get(ATTR_SONOFF_ALARM_VOLUME_LEVEL) == (1 if volume_rejected else 2)
    assert cluster.get(ATTR_SONOFF_ALARM_DURATION) == 10

    # Exercise zigpy's actual attribute serialization; only the radio write is mocked.
    cluster.write_attributes_raw.assert_awaited_once()
    written_attributes = cluster.write_attributes_raw.call_args.args[0]
    assert {attr.attrid: attr.value.value for attr in written_attributes} == {
        ATTR_SONOFF_ALARM_VOLUME_LEVEL: 2,
        ATTR_SONOFF_ALARM_DURATION: 10,
    }
