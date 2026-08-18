"""Tests for the Green Power quirk builder."""

from unittest.mock import MagicMock

import pytest
from zha.application.platforms.event import EntityEventTriggeredEvent, TriggeredEvent
from zha.quirks import DEVICE_REGISTRY, QUIRK_REGISTRY_ENTRY_ATTR
from zigpy.device import (
    GreenPowerCommandReceived,
    GreenPowerDevice as ZigpyGreenPowerDevice,
)
from zigpy.types import EUI64
from zigpy.zgp.commands import GPContactStatusPayload
from zigpy.zgp.types import ApplicationID, DeviceID, GPDCommandID, SrcID

from zhaquirks.builder import (
    EventDeviceClass,
    GreenPowerEventTrigger,
    GreenPowerQuirkBuilder,
)
from zhaquirks.builder.green_power import GreenPowerEventEntity, QuirkGreenPowerDevice


@pytest.fixture
def zigpy_gpd(MockAppController):
    """Create a commissioned SrcID-addressed zigpy GPD."""
    gpd = ZigpyGreenPowerDevice(
        MockAppController,
        application_id=ApplicationID.SrcID,
        src_id=SrcID(0x01700001),
    )
    gpd.device_id = DeviceID.OnOffSwitch
    gpd.commands = [
        GPDCommandID.Toggle,
        GPDCommandID.Press1of1,
        GPDCommandID.Release1of1,
    ]
    return gpd


def test_green_power_quirk_builder(zigpy_gpd):
    """Test matching and resolving a Green Power quirk."""
    with DEVICE_REGISTRY.preserve_state():
        entry = (
            GreenPowerQuirkBuilder()
            .applies_to(device_id=DeviceID.OnOffSwitch)
            .src_id_range(0x01700000, 0x0170FFFF)
            .filter(lambda device: GPDCommandID.Toggle in device.commands)
            .friendly_name(manufacturer="EnOcean", model="PTM 215Z")
            .add_to_registry()
        )

        assert DEVICE_REGISTRY.match_green_power_entry(zigpy_gpd) is entry

        resolved = DEVICE_REGISTRY.resolve(zigpy_gpd)
        assert resolved is zigpy_gpd
        assert getattr(resolved, QUIRK_REGISTRY_ENTRY_ATTR) is entry

        zha_device = entry.zha_device_factory(resolved, MagicMock())
        assert isinstance(zha_device, QuirkGreenPowerDevice)
        assert zha_device.manufacturer == "EnOcean"
        assert zha_device.model == "PTM 215Z"
        assert zha_device.name == "EnOcean PTM 215Z"


def test_green_power_quirk_builder_no_match(zigpy_gpd):
    """Test that a non-matching quirk leaves the device unquirked."""
    with DEVICE_REGISTRY.preserve_state():
        (
            GreenPowerQuirkBuilder()
            .applies_to(device_id=DeviceID.GenericSwitch)
            .add_to_registry()
        )
        (
            GreenPowerQuirkBuilder()
            .applies_to(device_id=DeviceID.OnOffSwitch)
            .src_id_range(0x00400000, 0x0040FFFF)
            .add_to_registry()
        )

        assert DEVICE_REGISTRY.match_green_power_entry(zigpy_gpd) is None
        assert DEVICE_REGISTRY.resolve(zigpy_gpd) is zigpy_gpd
        assert not hasattr(zigpy_gpd, QUIRK_REGISTRY_ENTRY_ATTR)


def test_green_power_quirk_builder_ieee_prefix(MockAppController):
    """Test matching an IEEE-addressed GPD by address prefix."""
    gpd = ZigpyGreenPowerDevice(
        MockAppController,
        application_id=ApplicationID.IEEE,
        ieee=EUI64.convert("04:cd:15:00:11:22:33:44"),
        endpoint=1,
    )

    with DEVICE_REGISTRY.preserve_state():
        entry = GreenPowerQuirkBuilder().ieee_prefix("04:cd:15").add_to_registry()

        assert DEVICE_REGISTRY.match_green_power_entry(gpd) is entry


def test_green_power_quirk_builder_requires_criteria():
    """Test that a quirk without matching criteria is rejected."""
    with pytest.raises(ValueError):
        GreenPowerQuirkBuilder().friendly_name(
            manufacturer="Acme", model="Switch"
        ).add_to_registry()

    with pytest.raises(ValueError):
        GreenPowerQuirkBuilder().applies_to()


def test_green_power_quirk_custom_device_class(zigpy_gpd):
    """Test that a custom ZHA device class is used by the factory."""

    class CustomGreenPowerDevice(QuirkGreenPowerDevice):
        """Custom quirk device class."""

    with DEVICE_REGISTRY.preserve_state():
        entry = (
            GreenPowerQuirkBuilder()
            .applies_to(device_id=DeviceID.OnOffSwitch)
            .device_class(CustomGreenPowerDevice)
            .add_to_registry()
        )

        zha_device = entry.zha_device_factory(zigpy_gpd, MagicMock())
        assert isinstance(zha_device, CustomGreenPowerDevice)


def test_green_power_quirk_event_entities(zigpy_gpd):
    """Test event entities declared by a Green Power quirk."""
    with DEVICE_REGISTRY.preserve_state():
        entry = (
            GreenPowerQuirkBuilder()
            .applies_to(device_id=DeviceID.OnOffSwitch)
            .event(
                {
                    "press": GreenPowerEventTrigger(
                        GPDCommandID.Press8BitVector, params={"contact_status": 0b0001}
                    ),
                    "release": GreenPowerEventTrigger(
                        GPDCommandID.Release8BitVector, params={"contact_status": 0}
                    ),
                },
                device_class=EventDeviceClass.BUTTON,
                unique_id_suffix="button_1",
                primary=True,
                fallback_name="Button 1",
            )
            .event(
                {"toggle": GreenPowerEventTrigger(GPDCommandID.Toggle)},
                device_class=EventDeviceClass.BUTTON,
                unique_id_suffix="button_2",
                fallback_name="Button 2",
            )
            .add_to_registry()
        )

        zha_device = entry.zha_device_factory(zigpy_gpd, MagicMock())
        entities = list(zha_device.discover_entities())
        assert len(entities) == 2
        assert all(isinstance(entity, GreenPowerEventEntity) for entity in entities)

        button_1, button_2 = entities
        assert button_1.unique_id == f"{zigpy_gpd.ieee}-button_1"
        assert button_1.event_types == ["press", "release"]
        assert button_1.device_class == EventDeviceClass.BUTTON
        assert button_1.fallback_name == "Button 1"
        assert button_1.primary
        assert button_2.unique_id == f"{zigpy_gpd.ieee}-button_2"
        assert not button_2.primary

        events: list[EntityEventTriggeredEvent] = []
        button_1.on_event(EntityEventTriggeredEvent.event, events.append)
        button_2.on_event(EntityEventTriggeredEvent.event, events.append)

        # A press of the first contact fires only the first entity
        zigpy_gpd.emit(
            GreenPowerCommandReceived.event_type,
            GreenPowerCommandReceived(
                device_ieee=str(zigpy_gpd.ieee),
                endpoint_id=0,
                command_id=GPDCommandID.Press8BitVector,
                command=GPContactStatusPayload(contact_status=0b0001),
            ),
        )
        assert [event.triggered for event in events] == [
            TriggeredEvent(
                event_type="press",
                event_attributes={"contact_status": 0b0001},
            )
        ]

        # A press of another contact fires nothing
        zigpy_gpd.emit(
            GreenPowerCommandReceived.event_type,
            GreenPowerCommandReceived(
                device_ieee=str(zigpy_gpd.ieee),
                endpoint_id=0,
                command_id=GPDCommandID.Press8BitVector,
                command=GPContactStatusPayload(contact_status=0b0010),
            ),
        )
        assert len(events) == 1

        # A toggle fires the second entity
        zigpy_gpd.emit(
            GreenPowerCommandReceived.event_type,
            GreenPowerCommandReceived(
                device_ieee=str(zigpy_gpd.ieee),
                endpoint_id=0,
                command_id=GPDCommandID.Toggle,
                command=None,
            ),
        )
        assert events[-1].triggered == TriggeredEvent(
            event_type="toggle", event_attributes={}
        )
        assert events[-1].unique_id == button_2.unique_id


def test_green_power_quirk_event_validation():
    """Test event entity declaration validation."""
    builder = GreenPowerQuirkBuilder().applies_to(device_id=DeviceID.OnOffSwitch)
    builder.event(
        {"toggle": GreenPowerEventTrigger(GPDCommandID.Toggle)},
        device_class=EventDeviceClass.BUTTON,
        primary=True,
        fallback_name="Button",
    )

    # No translation key and no device class
    with pytest.raises(ValueError):
        builder.event(
            {"toggle": GreenPowerEventTrigger(GPDCommandID.Toggle)},
            unique_id_suffix="other",
            fallback_name="Button",
        )

    # Duplicate unique_id_suffix
    with pytest.raises(ValueError):
        builder.event(
            {"toggle": GreenPowerEventTrigger(GPDCommandID.Toggle)},
            device_class=EventDeviceClass.BUTTON,
            fallback_name="Button",
        )

    # Second primary entity
    with pytest.raises(ValueError):
        builder.event(
            {"toggle": GreenPowerEventTrigger(GPDCommandID.Toggle)},
            device_class=EventDeviceClass.BUTTON,
            unique_id_suffix="other",
            primary=True,
            fallback_name="Button",
        )


def test_green_power_quirk_custom_entity_class(zigpy_gpd):
    """Test a quirk providing its own event entity class."""

    class CustomEvent(GreenPowerEventEntity):
        contact = 0b0010

    with DEVICE_REGISTRY.preserve_state():
        entry = (
            GreenPowerQuirkBuilder()
            .applies_to(device_id=DeviceID.OnOffSwitch)
            .event(
                {"press": GreenPowerEventTrigger(GPDCommandID.Press8BitVector)},
                entity_class=CustomEvent,
                device_class=EventDeviceClass.BUTTON,
                unique_id_suffix="button_1",
                fallback_name="Button 1",
            )
            .add_to_registry()
        )

        zha_device = entry.zha_device_factory(zigpy_gpd, MagicMock())
        (entity,) = zha_device.discover_entities()

        assert isinstance(entity, CustomEvent)
        assert entity.contact == 0b0010
