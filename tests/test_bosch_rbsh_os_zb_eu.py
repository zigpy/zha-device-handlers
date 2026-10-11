"""Tests for the Bosch outdoor siren quirk."""

import logging
from unittest import mock

import pytest
from zha.quirks import QUIRK_REGISTRY_ENTRY_ATTR, SIREN_BASIC
from zigpy.exceptions import ZigbeeException
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.security import IasWd, IasZone, WarningMode, WarningType
from zigpy.zcl.foundation import ZCLAttributeAccess

from tests.common import wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.bosch.rbsh_os_zb_eu import (
    BOSCH_MANUFACTURER_CODE,
    BoschAlarmMode,
    BoschCurrentPowerSource,
    BoschDeviceState,
    BoschPrimaryPowerSource,
    BoschSirenIasWd,
    BoschSirenIasZone,
    BoschSirenPowerConfiguration,
    BoschSirenVolume,
)
from zhaquirks.builder import EntityPlatform, EntityType
from zhaquirks.builder.metadata import (
    BinarySensorMetadata,
    ZCLCommandButtonMetadata,
    ZCLEnumMetadata,
    ZCLSensorMetadata,
)

zhaquirks.setup()

MODEL = "RBSH-OS-ZB-EU"

# Data bytes of the manufacturer specific commands, as the device expects them
ALARM_TRIGGER = 0x07
ALARM_STOP = 0x00
ACK_TAMPER = 0x02
ACK_POWER_OUTAGE = 0x04
CLUSTERS = {
    1: {
        PowerConfiguration.cluster_id: ClusterType.Server,
        IasZone.cluster_id: ClusterType.Server,
        IasWd.cluster_id: ClusterType.Server,
    }
}


@pytest.fixture
def siren(zigpy_device_from_v2_quirk):
    """Return a quirked outdoor siren."""
    return zigpy_device_from_v2_quirk("Bosch", MODEL, cluster_ids=CLUSTERS)


def quirk_definition(device):
    """Return the v2 quirk definition that was applied to a device."""
    entry = getattr(device, QUIRK_REGISTRY_ENTRY_ATTR)
    return entry.zha_device_factory.quirk_definition


def success_response(command_id: int) -> foundation.CommandSchema:
    """Return a successful default response to a command."""
    return foundation.GENERAL_COMMANDS[
        foundation.GeneralCommand.Default_Response
    ].schema(command_id=command_id, status=foundation.Status.SUCCESS)


def warning(mode: WarningMode) -> WarningType:
    """Return a warning of a mode."""
    result = WarningType()
    result.mode = mode
    return result


def status_change(zone_status: int):
    """Return the header and arguments of a zone status change notification."""
    command = IasZone.ClientCommandDefs.status_change_notification
    return (
        foundation.ZCLHeader.cluster(tsn=1, command_id=command.id),
        command.schema(zone_status=zone_status, extended_status=0, zone_id=0, delay=0),
    )


def test_friendly_name(siren):
    """Test that the siren is shown with its product code."""
    friendly_name = quirk_definition(siren).friendly_name

    assert friendly_name.manufacturer == "Bosch"
    assert friendly_name.model == "BSIR-EZ"


def test_attribute_definitions():
    """Test the ids, wire types and access of the manufacturer attributes.

    The device refuses a write with an enum8 data type, so everything that is written
    must be a plain uint8 or uint16 on the wire.
    """
    expected = {
        BoschSirenIasWd: {
            "siren_duration": (0xA000, t.uint8_t, "rwp"),
            "alarm_mode": (0xA001, t.uint8_t, "rwp"),
            "siren_volume": (0xA002, t.uint8_t, "rwp"),
            "siren_delay": (0xA003, t.uint16_t, "rwp"),
            "light_delay": (0xA004, t.uint16_t, "rwp"),
            "light_duration": (0xA005, t.uint8_t, "rwp"),
            "device_state": (0xA006, t.uint8_t, "rp"),
        },
        BoschSirenPowerConfiguration: {
            "solar_panel_voltage": (0xA000, t.uint16_t, "rp"),
            "primary_power_source": (0xA002, t.uint8_t, "rwp"),
        },
        BoschSirenIasZone: {
            "current_power_source": (0xA001, t.uint8_t, "rp"),
        },
    }

    for cluster, attributes in expected.items():
        for name, (attr_id, attr_type, access) in attributes.items():
            attr = cluster.find_attribute(name)
            assert attr.id == attr_id
            assert attr.type is attr_type
            assert attr.access == ZCLAttributeAccess.from_str(access)
            assert attr.manufacturer_code == BOSCH_MANUFACTURER_CODE


def test_command_definitions():
    """Test the ids of the manufacturer specific commands."""
    alarm_control = BoschSirenIasWd.ServerCommandDefs.alarm_control
    acknowledge = BoschSirenIasZone.ServerCommandDefs.acknowledge_status_change

    assert alarm_control.id == 0xF0
    assert alarm_control.manufacturer_code == BOSCH_MANUFACTURER_CODE
    assert acknowledge.id == 0xF3
    assert acknowledge.manufacturer_code == BOSCH_MANUFACTURER_CODE


def test_siren_is_basic_and_default_zone_sensor_is_replaced(siren):
    """Test the basic siren feature and the removal of ZHA's IAS zone sensor."""
    definition = quirk_definition(siren)

    assert {feature.feature for feature in definition.exposes_features} == {SIREN_BASIC}

    (prevented,) = definition.disabled_default_entities
    assert prevented.cluster_id == IasZone.cluster_id

    class IASZone:
        """Stand in for ZHA's own IAS zone sensor."""

    class BinarySensor:
        """Stand in for an entity that the quirk creates."""

    assert prevented.function(IASZone())
    assert not prevented.function(BinarySensor())


def test_entities(siren):
    """Test the entities that the quirk creates."""
    entities = {
        (meta.entity_platform, meta.unique_id_suffix or meta.attribute_name): meta
        for meta in quirk_definition(siren).entity_metadata
        if not isinstance(meta, ZCLCommandButtonMetadata)
    }

    assert {
        key: (meta.entity_type, meta.cluster_id) for key, meta in entities.items()
    } == {
        (EntityPlatform.SELECT, "alarm_mode"): (EntityType.CONFIG, IasWd.cluster_id),
        (EntityPlatform.SELECT, "siren_volume"): (EntityType.CONFIG, IasWd.cluster_id),
        (EntityPlatform.SELECT, "primary_power_source"): (
            EntityType.CONFIG,
            PowerConfiguration.cluster_id,
        ),
        (EntityPlatform.NUMBER, "siren_duration"): (
            EntityType.CONFIG,
            IasWd.cluster_id,
        ),
        (EntityPlatform.NUMBER, "light_duration"): (
            EntityType.CONFIG,
            IasWd.cluster_id,
        ),
        (EntityPlatform.NUMBER, "siren_delay"): (EntityType.CONFIG, IasWd.cluster_id),
        (EntityPlatform.NUMBER, "light_delay"): (EntityType.CONFIG, IasWd.cluster_id),
        (EntityPlatform.SENSOR, "device_state"): (
            EntityType.DIAGNOSTIC,
            IasWd.cluster_id,
        ),
        (EntityPlatform.SENSOR, "current_power_source"): (
            EntityType.DIAGNOSTIC,
            IasZone.cluster_id,
        ),
        (EntityPlatform.SENSOR, "solar_panel_voltage"): (
            EntityType.DIAGNOSTIC,
            PowerConfiguration.cluster_id,
        ),
        (EntityPlatform.BINARY_SENSOR, "external_trigger"): (
            EntityType.STANDARD,
            IasZone.cluster_id,
        ),
        (EntityPlatform.BINARY_SENSOR, "tamper"): (
            EntityType.DIAGNOSTIC,
            IasZone.cluster_id,
        ),
        (EntityPlatform.BINARY_SENSOR, "power_outage"): (
            EntityType.DIAGNOSTIC,
            IasZone.cluster_id,
        ),
    }

    for key, enum_class in {
        (EntityPlatform.SELECT, "alarm_mode"): BoschAlarmMode,
        (EntityPlatform.SELECT, "siren_volume"): BoschSirenVolume,
        (EntityPlatform.SELECT, "primary_power_source"): BoschPrimaryPowerSource,
        (EntityPlatform.SENSOR, "device_state"): BoschDeviceState,
        (EntityPlatform.SENSOR, "current_power_source"): BoschCurrentPowerSource,
    }.items():
        assert isinstance(entities[key], ZCLEnumMetadata)
        assert entities[key].enum is enum_class

    assert isinstance(
        entities[(EntityPlatform.SENSOR, "solar_panel_voltage")], ZCLSensorMetadata
    )
    assert entities[(EntityPlatform.SENSOR, "solar_panel_voltage")].divisor == 10


def test_numbers_fit_the_device(siren):
    """Test the limits of the delay and duration numbers."""
    numbers = {
        meta.attribute_name: (meta.min, meta.max, meta.step)
        for meta in quirk_definition(siren).entity_metadata
        if meta.entity_platform == EntityPlatform.NUMBER
    }

    assert numbers == {
        "siren_duration": (1, 15, 1),
        "light_duration": (1, 15, 1),
        "siren_delay": (0, 180, 1),
        "light_delay": (0, 180, 1),
    }


def test_stop_button(siren):
    """Test that the only button stops the alarm."""
    (button,) = (
        meta
        for meta in quirk_definition(siren).entity_metadata
        if isinstance(meta, ZCLCommandButtonMetadata)
    )

    assert button.cluster_id == IasWd.cluster_id
    assert button.command_name == "alarm_control"
    assert dict(button.kwargs) == {"data": ALARM_STOP}
    assert button.unique_id_suffix == "stop_alarm"


@pytest.mark.parametrize(
    ("flag", "suffix"),
    [
        (IasZone.ZoneStatus.Alarm_1, "external_trigger"),
        (IasZone.ZoneStatus.Tamper, "tamper"),
        (IasZone.ZoneStatus.Alarm_2, "power_outage"),
    ],
)
def test_zone_status_sensors(siren, flag, suffix):
    """Test that each binary sensor follows its own bit of the zone status."""
    (sensor,) = (
        meta
        for meta in quirk_definition(siren).entity_metadata
        if isinstance(meta, BinarySensorMetadata) and meta.unique_id_suffix == suffix
    )

    everything = IasZone.ZoneStatus(0xFFFF)
    assert sensor.attribute_converter(flag)
    assert sensor.attribute_converter(everything)
    assert not sensor.attribute_converter(IasZone.ZoneStatus(0))
    assert not sensor.attribute_converter(everything & ~flag)


async def test_trigger_and_stop_use_the_manufacturer_command(siren):
    """Test that ZHA's siren calls become the Bosch alarm command."""
    cluster = siren.endpoints[1].ias_wd
    cluster.request = mock.AsyncMock(
        return_value=success_response(
            BoschSirenIasWd.ServerCommandDefs.alarm_control.id
        )
    )

    # ZHA sends a tone, level and duration, none of which the device uses
    await cluster.start_warning(
        warning=warning(WarningMode.Emergency),
        warning_duration=300,
        strobe_duty_cycle=0,
        stobe_level=0,
    )
    await cluster.start_warning(warning=warning(WarningMode.Stop), warning_duration=5)

    trigger, stop = cluster.request.await_args_list
    for call, data in ((trigger, ALARM_TRIGGER), (stop, ALARM_STOP)):
        assert call.args[1] == 0xF0
        assert call.kwargs["manufacturer"] == BOSCH_MANUFACTURER_CODE
        assert call.kwargs["data"] == data


async def test_refused_alarm_command_raises(siren):
    """Test that a refused alarm command is reported to ZHA."""
    cluster = siren.endpoints[1].ias_wd
    cluster.request = mock.AsyncMock(
        return_value=foundation.GENERAL_COMMANDS[
            foundation.GeneralCommand.Default_Response
        ].schema(command_id=0xF0, status=foundation.Status.FAILURE)
    )

    with pytest.raises(ZigbeeException, match="refused"):
        await cluster.start_warning(
            warning=warning(WarningMode.Emergency), warning_duration=5
        )


async def test_squawk_is_not_supported(siren):
    """Test that squawking is refused."""
    with pytest.raises(ZigbeeException, match="squawk"):
        await siren.endpoints[1].ias_wd.squawk()


@pytest.mark.parametrize(
    ("zone_status", "acknowledged"),
    [
        (IasZone.ZoneStatus.Tamper, [ACK_TAMPER]),
        (IasZone.ZoneStatus.Alarm_2, [ACK_POWER_OUTAGE]),
        (
            IasZone.ZoneStatus.Tamper | IasZone.ZoneStatus.Alarm_2,
            [ACK_TAMPER, ACK_POWER_OUTAGE],
        ),
        (IasZone.ZoneStatus.Alarm_1, []),
        (IasZone.ZoneStatus(0), []),
    ],
)
async def test_status_changes_are_acknowledged(siren, zone_status, acknowledged):
    """Test that the tamper and power outage bits are acknowledged to the device."""
    cluster = siren.endpoints[1].ias_zone
    cluster.request = mock.AsyncMock()

    cluster.handle_cluster_request(*status_change(zone_status))
    await wait_for_zigpy_tasks()

    assert [call.kwargs["data"] for call in cluster.request.await_args_list] == (
        acknowledged
    )
    for call in cluster.request.await_args_list:
        assert call.args[1] == 0xF3
        assert call.kwargs["manufacturer"] == BOSCH_MANUFACTURER_CODE


async def test_other_commands_are_not_acknowledged(siren):
    """Test that only a status change notification is acknowledged."""
    cluster = siren.endpoints[1].ias_zone
    cluster.request = mock.AsyncMock()

    header = foundation.ZCLHeader.cluster(
        tsn=1, command_id=IasZone.ClientCommandDefs.enroll.id
    )
    args = IasZone.ClientCommandDefs.enroll.schema(zone_type=0, manufacturer_code=0)
    cluster.handle_cluster_request(header, args)
    await wait_for_zigpy_tasks()

    cluster.request.assert_not_awaited()


async def test_failed_acknowledgement_is_logged(siren, caplog):
    """Test that a failed acknowledgement is logged and does not raise."""
    cluster = siren.endpoints[1].ias_zone
    cluster.request = mock.AsyncMock(side_effect=ZigbeeException("no ack"))

    with caplog.at_level(logging.WARNING):
        cluster.handle_cluster_request(*status_change(IasZone.ZoneStatus.Tamper))
        await wait_for_zigpy_tasks()

    assert "Acknowledging zone status 0x02 failed" in caplog.text
