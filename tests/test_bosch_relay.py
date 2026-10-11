"""Tests for the Bosch Relay (potential free) quirk."""

from unittest import mock

import pytest
from zha.quirks import QUIRK_REGISTRY_ENTRY_ATTR
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation

import zhaquirks
from zhaquirks.bosch.rbsh_mmr_zb_eu import (
    BOSCH_MFG_CODE,
    BoschActuatorType,
    BoschDeviceMode,
    BoschRelayControl,
    BoschSwitchType,
)
from zhaquirks.builder import EntityType
from zhaquirks.builder.metadata import NumberMetadata, SwitchMetadata, ZCLEnumMetadata

zhaquirks.setup()

CLUSTER_ID = BoschRelayControl.cluster_id
ATTRS = BoschRelayControl.AttributeDefs

RELAY_CLUSTERS = {
    1: {
        0x0003: ClusterType.Server,
        0x0004: ClusterType.Server,
        0x0005: ClusterType.Server,
        0x0006: ClusterType.Server,
        0x0B05: ClusterType.Server,
        CLUSTER_ID: ClusterType.Server,
        0x000A: ClusterType.Client,
        0x0019: ClusterType.Client,
    }
}


@pytest.fixture
def relay(zigpy_device_from_v2_quirk):
    """Return a relay with the quirk applied."""
    return zigpy_device_from_v2_quirk(
        "Bosch", "RBSH-MMR-ZB-EU", cluster_ids=RELAY_CLUSTERS
    )


def _cluster(relay):
    return relay.endpoints[1].in_clusters[CLUSTER_ID]


def _definition(relay):
    """Return the v2 quirk definition that was applied to a device."""
    entry = getattr(relay, QUIRK_REGISTRY_ENTRY_ATTR)
    return entry.zha_device_factory.quirk_definition


def test_quirk_applied(relay):
    """Test that the cluster is replaced and the relay is shown as BMCT-RZ."""
    assert isinstance(_cluster(relay), BoschRelayControl)

    friendly_name = _definition(relay).friendly_name
    assert friendly_name.manufacturer == "Bosch"
    assert friendly_name.model == "BMCT-RZ"


def test_entities(relay):
    """Test the configuration entities that are created."""
    entities = {e.attribute_name: e for e in _definition(relay).entity_metadata}

    assert set(entities) == {
        ATTRS.switch_type.name,
        ATTRS.decoupled_mode.name,
        ATTRS.actuator_type.name,
        ATTRS.child_lock.name,
        ATTRS.device_mode.name,
        ATTRS.pulse_length.name,
        ATTRS.auto_off_enabled.name,
        ATTRS.auto_off_time.name,
    }
    assert all(e.cluster_id == CLUSTER_ID for e in entities.values())
    assert all(e.entity_type == EntityType.CONFIG for e in entities.values())

    assert isinstance(entities[ATTRS.switch_type.name], ZCLEnumMetadata)
    assert isinstance(entities[ATTRS.actuator_type.name], ZCLEnumMetadata)
    assert isinstance(entities[ATTRS.device_mode.name], ZCLEnumMetadata)
    assert isinstance(entities[ATTRS.child_lock.name], SwitchMetadata)
    assert isinstance(entities[ATTRS.decoupled_mode.name], SwitchMetadata)
    assert isinstance(entities[ATTRS.auto_off_enabled.name], SwitchMetadata)
    assert isinstance(entities[ATTRS.pulse_length.name], NumberMetadata)
    assert isinstance(entities[ATTRS.auto_off_time.name], NumberMetadata)

    # the device mode is derived from the pulse length, the rest is read from the relay
    for name, entity in entities.items():
        assert entity.attribute_initialized_from_cache is (
            name == ATTRS.device_mode.name
        )


def test_pulse_length_slider(relay):
    """Test that the pulse length is a slider in half seconds."""
    entities = {e.attribute_name: e for e in _definition(relay).entity_metadata}
    pulse_length = entities[ATTRS.pulse_length.name]

    # ZHA writes int(value / multiplier), so a 0.1 step would lose a tenth of a
    # second for a third of the values
    assert pulse_length.mode == "slider"
    assert (pulse_length.min, pulse_length.max) == (0.5, 20)
    assert pulse_length.step == 0.5
    assert pulse_length.multiplier == 0.1


@pytest.mark.parametrize(
    ("attribute", "value", "wire"),
    [
        (ATTRS.child_lock.name, True, "08001001"),
        (ATTRS.decoupled_mode.name, 1, "31002001"),
        (ATTRS.auto_off_enabled.name, True, "06001001"),
        (ATTRS.pulse_length.name, 25, "2400211900"),
        (ATTRS.auto_off_time.name, 600, "0700215802"),
        (ATTRS.switch_type.name, BoschSwitchType.Rocker_switch, "01003007"),
        (ATTRS.actuator_type.name, BoschActuatorType.Normally_open, "34003001"),
    ],
)
async def test_write_wire_format(relay, attribute, value, wire):
    """Test that attributes are written with the data type the relay uses."""
    cluster = _cluster(relay)
    ok = [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

    with mock.patch.object(cluster, "request", mock.AsyncMock(return_value=ok)) as req:
        await cluster.write_attributes({attribute: value})

    assert req.mock_calls[0].args[3][0].serialize().hex() == wire
    assert req.mock_calls[0].kwargs["manufacturer"] == BOSCH_MFG_CODE


@pytest.mark.parametrize(
    ("pulse_length", "mode"),
    [
        (0, BoschDeviceMode.Switch),
        (10, BoschDeviceMode.Pulsed),
        (200, BoschDeviceMode.Pulsed),
    ],
)
def test_device_mode_follows_pulse_length(relay, pulse_length, mode):
    """Test that the device mode is derived from a reported pulse length."""
    cluster = _cluster(relay)
    cluster.update_attribute(ATTRS.pulse_length.id, pulse_length)

    assert cluster.get(ATTRS.device_mode.name) == mode


async def _write(relay, attributes):
    """Write attributes and return the records that were sent to the relay."""
    cluster = _cluster(relay)
    ok = [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

    with mock.patch.object(cluster, "request", mock.AsyncMock(return_value=ok)) as req:
        await cluster.write_attributes(attributes)

    return [record.serialize().hex() for record in req.mock_calls[0].args[3]]


async def test_device_mode_writes_pulse_length(relay):
    """Test that pulsed restores the last pulse length and switch writes 0."""
    cluster = _cluster(relay)
    pulse_length = ATTRS.pulse_length.name
    device_mode = ATTRS.device_mode.name

    # the first time the default of 1.0 second is used
    assert await _write(relay, {device_mode: BoschDeviceMode.Pulsed}) == ["2400210a00"]
    assert cluster.get(device_mode) == BoschDeviceMode.Pulsed

    # a longer pulse is remembered across switch mode
    await _write(relay, {pulse_length: 35})
    assert await _write(relay, {device_mode: BoschDeviceMode.Switch}) == ["2400210000"]
    assert cluster.get(device_mode) == BoschDeviceMode.Switch
    assert await _write(relay, {device_mode: BoschDeviceMode.Pulsed}) == ["2400212300"]


async def test_pulse_length_write_updates_device_mode(relay):
    """Test that writing a pulse length moves the device mode."""
    cluster = _cluster(relay)

    await _write(relay, {ATTRS.pulse_length.name: 20})
    assert cluster.get(ATTRS.device_mode.name) == BoschDeviceMode.Pulsed

    await _write(relay, {ATTRS.pulse_length.name: 0})
    assert cluster.get(ATTRS.device_mode.name) == BoschDeviceMode.Switch


async def test_explicit_pulse_length_wins_over_device_mode(relay):
    """Test that a pulse length in the same write takes precedence."""
    wire = await _write(
        relay,
        {
            ATTRS.device_mode.name: BoschDeviceMode.Switch,
            ATTRS.pulse_length.name: 50,
        },
    )

    assert wire == ["2400213200"]


async def test_other_writes_are_untouched(relay):
    """Test that writes without a device mode are passed on as they are."""
    assert await _write(relay, {ATTRS.child_lock.name: True}) == ["08001001"]


@pytest.mark.parametrize("command", [0x03, 0x04])
@pytest.mark.parametrize(
    ("status", "duration", "event", "seconds"),
    [
        (0, 0, "press_released", 0.0),
        (1, 5, "hold", 0.5),
        (1, 0, "hold_released", 0.0),
        (2, 0, "closed", 0.0),
        (3, 0, "opened", 0.0),
    ],
)
async def test_switch_events(relay, command, status, duration, event, seconds):
    """Test that the input commands of the relay are emitted as named events."""
    listener = mock.MagicMock()
    _cluster(relay).add_listener(listener)

    # Frame: 0x1D (cluster specific, manufacturer specific, server-to-client,
    #        disable-default-rsp), manufacturer code 0x1209, TSN=7, command,
    #        status, duration
    relay.packet_received(
        t.ZigbeePacket(
            profile_id=260,
            cluster_id=CLUSTER_ID,
            src_ep=1,
            dst_ep=1,
            data=t.SerializableBytes(
                bytes([0x1D, 0x09, 0x12, 0x07, command, status, duration])
            ),
        )
    )

    listener.zha_send_event.assert_called_once_with(event, {"duration": seconds})


def test_device_automation_triggers(relay):
    """Test that the triggers match the events of the switch."""
    triggers = _definition(relay).device_automation_triggers

    assert {t["command"] for t in triggers.values()} == {
        "press_released",
        "hold",
        "hold_released",
        "closed",
        "opened",
    }
