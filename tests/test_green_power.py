"""Tests for the Green Power quirk builder."""

import inspect
from typing import Any
from unittest.mock import MagicMock

import pytest
from zha.application.platforms.event import (
    BaseEvent,
    EntityEventTriggeredEvent,
    TriggeredEvent,
)
from zha.application.platforms.sensor import Sensor
from zha.quirks import DEVICE_REGISTRY, QUIRK_REGISTRY_ENTRY_ATTR, DeviceRegistry
from zha.zigbee.device import GreenPowerDevice
from zigpy.device import (
    GreenPowerCommandReceived,
    GreenPowerDevice as ZigpyGreenPowerDevice,
)
from zigpy.types import EUI64
from zigpy.zgp.types import ApplicationID, DeviceID, GPDCommandID, SrcID

from zhaquirks.builder import EventDeviceClass, GreenPowerQuirkBuilder
from zhaquirks.builder.green_power import QuirkGreenPowerDevice


class CommandEvent(BaseEvent):
    """Event entity firing an event type for a single GPD command."""

    _attr_device_class = EventDeviceClass.BUTTON

    def __init__(
        self,
        device: GreenPowerDevice,
        *,
        command_id: GPDCommandID,
        event_type: str,
        **kwargs: Any,
    ) -> None:
        """Initialize the event entity."""
        self._command_id = command_id
        self._attr_event_types = [event_type]

        super().__init__(device, **kwargs)

    def on_add(self) -> None:
        """Subscribe to the commands sent by the device."""
        super().on_add()
        self._on_remove_callbacks.append(
            self.device.device.on_event(
                GreenPowerCommandReceived.event_type, self._handle_gp_command
            )
        )

    def _handle_gp_command(self, event: GreenPowerCommandReceived) -> None:
        """Fire the entity's event type for its own command."""
        if event.command_id == self._command_id:
            self._trigger_event(self._attr_event_types[0])


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
    zigpy_gpd.gpd_manufacturer_id = 0x1234
    zigpy_gpd.gpd_model_id = 0x5678

    registry = DeviceRegistry()

    entry = (
        GreenPowerQuirkBuilder(registry=registry)
        .applies_to(
            device_id=DeviceID.OnOffSwitch, manufacturer_id=0x1234, model_id=0x5678
        )
        .src_id_range(0x01700000, 0x0170FFFF)
        .filter(lambda device: GPDCommandID.Toggle in device.commands)
        .friendly_name(manufacturer="EnOcean", model="PTM 215Z")
        .add_to_registry()
    )

    assert registry.match_green_power_entry(zigpy_gpd) is entry

    resolved = registry.resolve(zigpy_gpd)
    assert resolved is zigpy_gpd
    assert getattr(resolved, QUIRK_REGISTRY_ENTRY_ATTR) is entry

    zha_device = entry.zha_device_factory(resolved, MagicMock())
    assert isinstance(zha_device, QuirkGreenPowerDevice)
    assert zha_device.manufacturer == "EnOcean"
    assert zha_device.model == "PTM 215Z"
    assert zha_device.name == "EnOcean PTM 215Z"
    assert zha_device.quirk_metadata.friendly_manufacturer == "EnOcean"
    assert zha_device.quirk_metadata.friendly_model == "PTM 215Z"


def test_green_power_quirk_builder_no_match(zigpy_gpd):
    """Test that a non-matching quirk leaves the device unquirked."""
    registry = DeviceRegistry()

    (
        GreenPowerQuirkBuilder(registry=registry)
        .applies_to(device_id=DeviceID.GenericSwitch)
        .friendly_name(manufacturer="Acme", model="Switch")
        .add_to_registry()
    )
    (
        GreenPowerQuirkBuilder(registry=registry)
        .applies_to(device_id=DeviceID.OnOffSwitch)
        .src_id_range(0x00400000, 0x0040FFFF)
        .friendly_name(manufacturer="Acme", model="Switch")
        .add_to_registry()
    )

    assert registry.match_green_power_entry(zigpy_gpd) is None
    assert registry.resolve(zigpy_gpd) is zigpy_gpd
    assert not hasattr(zigpy_gpd, QUIRK_REGISTRY_ENTRY_ATTR)


def test_green_power_quirk_builder_ieee_prefix(MockAppController):
    """Test matching an IEEE-addressed GPD by address prefix."""
    gpd = ZigpyGreenPowerDevice(
        MockAppController,
        application_id=ApplicationID.IEEE,
        ieee=EUI64.convert("04:cd:15:00:11:22:33:44"),
    )

    registry = DeviceRegistry()

    entry = (
        GreenPowerQuirkBuilder(registry=registry)
        .ieee_prefix("04:cd:15")
        .friendly_name(manufacturer="Acme", model="Switch")
        .add_to_registry()
    )

    assert registry.match_green_power_entry(gpd) is entry


def test_green_power_quirk_builder_requires_criteria():
    """Test that a quirk without matching criteria is rejected."""
    with pytest.raises(ValueError):
        GreenPowerQuirkBuilder().friendly_name(
            manufacturer="Acme", model="Switch"
        ).add_to_registry()

    with pytest.raises(ValueError):
        GreenPowerQuirkBuilder().applies_to()


def test_green_power_quirk_builder_requires_friendly_name():
    """Test that a quirk without a friendly name is rejected."""
    with pytest.raises(ValueError):
        GreenPowerQuirkBuilder().applies_to(
            device_id=DeviceID.OnOffSwitch
        ).add_to_registry()


def test_green_power_quirk_custom_device_class(zigpy_gpd):
    """Test that a custom ZHA device class is used by the factory."""

    class CustomGreenPowerDevice(QuirkGreenPowerDevice):
        """Custom quirk device class."""

    registry = DeviceRegistry()

    entry = (
        GreenPowerQuirkBuilder(registry=registry)
        .applies_to(device_id=DeviceID.OnOffSwitch)
        .device_class(CustomGreenPowerDevice)
        .friendly_name(manufacturer="Acme", model="Switch")
        .add_to_registry()
    )

    zha_device = entry.zha_device_factory(zigpy_gpd, MagicMock())
    assert isinstance(zha_device, CustomGreenPowerDevice)


def test_green_power_quirk_invalid_device_class():
    """Test that a device class not based on `QuirkGreenPowerDevice` is rejected."""
    with pytest.raises(TypeError):
        GreenPowerQuirkBuilder().device_class(GreenPowerDevice)


def test_green_power_quirk_entities(zigpy_gpd):
    """Test entities declared by a Green Power quirk."""
    registry = DeviceRegistry()

    entry = (
        GreenPowerQuirkBuilder(registry=registry)
        .applies_to(device_id=DeviceID.OnOffSwitch)
        .adds_entity(
            CommandEvent,
            command_id=GPDCommandID.Press1of1,
            event_type="press",
            unique_id_suffix="button_1",
            primary=True,
            fallback_name="Button 1",
        )
        .adds_entity(
            CommandEvent,
            command_id=GPDCommandID.Toggle,
            event_type="toggle",
            unique_id_suffix="button_2",
            fallback_name="Button 2",
        )
        .friendly_name(manufacturer="Acme", model="Switch")
        .add_to_registry()
    )

    zha_device = entry.zha_device_factory(zigpy_gpd, MagicMock())
    entities = list(zha_device.discover_entities())
    assert len(entities) == 2

    button_1, button_2 = entities
    assert button_1.unique_id == f"{zigpy_gpd.ieee}-button_1"
    assert button_1.event_types == ["press"]
    assert button_1.device_class == EventDeviceClass.BUTTON
    assert button_1.fallback_name == "Button 1"
    assert button_1.primary
    assert button_2.unique_id == f"{zigpy_gpd.ieee}-button_2"
    assert button_2.event_types == ["toggle"]
    assert not button_2.primary

    events: list[EntityEventTriggeredEvent] = []
    for entity in entities:
        entity.on_add()
        entity.on_event(EntityEventTriggeredEvent.event, events.append)

    # A press fires only the first entity
    zigpy_gpd.emit(
        GreenPowerCommandReceived.event_type,
        GreenPowerCommandReceived(
            device_ieee=str(zigpy_gpd.ieee),
            endpoint_id=0,
            command_id=GPDCommandID.Press1of1,
            command=None,
        ),
    )
    assert [(event.unique_id, event.triggered) for event in events] == [
        (
            button_1.unique_id,
            TriggeredEvent(event_type="press", event_attributes={}),
        )
    ]

    # A toggle fires only the second
    zigpy_gpd.emit(
        GreenPowerCommandReceived.event_type,
        GreenPowerCommandReceived(
            device_ieee=str(zigpy_gpd.ieee),
            endpoint_id=0,
            command_id=GPDCommandID.Toggle,
            command=None,
        ),
    )
    assert events[-1].unique_id == button_2.unique_id
    assert events[-1].triggered == TriggeredEvent(
        event_type="toggle", event_attributes={}
    )


def test_green_power_quirk_duplicate_unique_id_suffix():
    """Test that two entities with the same unique ID suffix are rejected."""
    builder = GreenPowerQuirkBuilder().adds_entity(
        CommandEvent,
        command_id=GPDCommandID.Press1of1,
        event_type="press",
        unique_id_suffix="button",
        fallback_name="Button 1",
    )

    with pytest.raises(ValueError):
        builder.adds_entity(
            CommandEvent,
            command_id=GPDCommandID.Toggle,
            event_type="toggle",
            unique_id_suffix="button",
            fallback_name="Button 2",
        )


def test_green_power_quirk_entity_arguments():
    """Test that only device-bound entities without their own unique ID are added."""
    builder = GreenPowerQuirkBuilder()

    with pytest.raises(TypeError):
        builder.adds_entity(
            Sensor,
            attribute_name="present_value",
            unique_id_suffix="sensor",
            fallback_name="Sensor",
        )

    with pytest.raises(ValueError):
        builder.adds_entity(
            CommandEvent,
            command_id=GPDCommandID.Toggle,
            event_type="toggle",
            unique_id="custom",
            unique_id_suffix="button",
            fallback_name="Button",
        )


class FailingEvent(CommandEvent):
    """Event entity that fails to be created."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Fail to initialize."""
        raise RuntimeError("Failed to initialize")


async def test_green_power_quirk_failing_entity_skipped(zigpy_gpd, caplog):
    """Test that an entity failing to be created does not stop the others."""
    registry = DeviceRegistry()

    entry = (
        GreenPowerQuirkBuilder(registry=registry)
        .applies_to(device_id=DeviceID.OnOffSwitch)
        .adds_entity(
            FailingEvent,
            command_id=GPDCommandID.Toggle,
            event_type="toggle",
            unique_id_suffix="failing",
            fallback_name="Failing",
        )
        .adds_entity(
            CommandEvent,
            command_id=GPDCommandID.Toggle,
            event_type="toggle",
            unique_id_suffix="button",
            fallback_name="Button",
        )
        .friendly_name(manufacturer="Acme", model="Switch")
        .add_to_registry()
    )

    zha_device = entry.zha_device_factory(zigpy_gpd, MagicMock())
    (entity,) = zha_device.discover_entities()

    assert type(entity) is CommandEvent
    assert "Failed to create added entity" in caplog.text


async def test_green_power_quirk_entity_removed(zigpy_gpd):
    """Test that a removed entity stops listening for GPD commands."""
    registry = DeviceRegistry()

    entry = (
        GreenPowerQuirkBuilder(registry=registry)
        .applies_to(device_id=DeviceID.OnOffSwitch)
        .adds_entity(
            CommandEvent,
            command_id=GPDCommandID.Toggle,
            event_type="toggle",
            unique_id_suffix="button",
            fallback_name="Button",
        )
        .friendly_name(manufacturer="Acme", model="Switch")
        .add_to_registry()
    )

    zha_device = entry.zha_device_factory(zigpy_gpd, MagicMock())
    (entity,) = zha_device.discover_entities()
    entity.on_add()

    events: list[EntityEventTriggeredEvent] = []
    entity.on_event(EntityEventTriggeredEvent.event, events.append)

    toggle = GreenPowerCommandReceived(
        device_ieee=str(zigpy_gpd.ieee),
        endpoint_id=0,
        command_id=GPDCommandID.Toggle,
        command=None,
    )

    zigpy_gpd.emit(GreenPowerCommandReceived.event_type, toggle)
    assert len(events) == 1

    await entity.on_remove()

    zigpy_gpd.emit(GreenPowerCommandReceived.event_type, toggle)
    assert len(events) == 1


def test_green_power_quirk_builder_source(zigpy_gpd):
    """Test that the registry entry points at the quirk's own definition."""
    registry = DeviceRegistry()

    builder = GreenPowerQuirkBuilder(registry=registry)
    line = inspect.currentframe().f_lineno - 1

    entry = (
        builder.applies_to(device_id=DeviceID.OnOffSwitch)
        .friendly_name(manufacturer="Acme", model="Switch")
        .add_to_registry()
    )

    assert entry.source.module == __name__
    assert entry.source.file == __file__
    assert entry.source.line == line
    assert entry.source.label == "(Acme / Switch)"


def test_green_power_quirk_builder_default_registry():
    """Test that the builder defaults to the global registry."""
    assert GreenPowerQuirkBuilder().registry is DEVICE_REGISTRY


def test_green_power_quirk_builder_registry_override(zigpy_gpd):
    """Test that `add_to_registry` registers in the given registry only."""
    builder_registry = DeviceRegistry()
    registry = DeviceRegistry()

    entry = (
        GreenPowerQuirkBuilder(registry=builder_registry)
        .applies_to(device_id=DeviceID.OnOffSwitch)
        .friendly_name(manufacturer="Acme", model="Switch")
        .add_to_registry(registry)
    )

    assert registry.match_green_power_entry(zigpy_gpd) is entry
    assert builder_registry.match_green_power_entry(zigpy_gpd) is None


def test_green_power_quirk_builder_int_device_id(zigpy_gpd):
    """Test that a plain integer device ID is accepted."""
    registry = DeviceRegistry()

    builder = GreenPowerQuirkBuilder(registry=registry).applies_to(device_id=0x02)
    assert builder.device_id is DeviceID.OnOffSwitch

    entry = builder.friendly_name(manufacturer="Acme", model="Switch").add_to_registry()
    assert registry.match_green_power_entry(zigpy_gpd) is entry


def test_green_power_quirk_builder_applies_to_accumulates():
    """Test that repeated `applies_to` calls only set the given fields."""
    builder = (
        GreenPowerQuirkBuilder()
        .applies_to(device_id=DeviceID.OnOffSwitch)
        .applies_to(manufacturer_id=0x1234)
        .applies_to(model_id=0x5678)
    )

    assert builder.device_id is DeviceID.OnOffSwitch
    assert builder.manufacturer_id == 0x1234
    assert builder.model_id == 0x5678


@pytest.mark.parametrize(
    ("manufacturer_id", "model_id", "commands", "matches"),
    [
        (0x1234, 0x5678, [GPDCommandID.Toggle], True),
        (0x1235, 0x5678, [GPDCommandID.Toggle], False),
        (0x1234, 0x5679, [GPDCommandID.Toggle], False),
        (None, None, [GPDCommandID.Toggle], False),
        (0x1234, 0x5678, [GPDCommandID.Press1of1], False),
    ],
)
def test_green_power_quirk_builder_every_criterion_must_match(
    zigpy_gpd, manufacturer_id, model_id, commands, matches
):
    """Test that a quirk only matches when all of its criteria do."""
    zigpy_gpd.gpd_manufacturer_id = manufacturer_id
    zigpy_gpd.gpd_model_id = model_id
    zigpy_gpd.commands = commands

    registry = DeviceRegistry()

    entry = (
        GreenPowerQuirkBuilder(registry=registry)
        .applies_to(manufacturer_id=0x1234, model_id=0x5678)
        .filter(lambda device: GPDCommandID.Toggle in device.commands)
        .friendly_name(manufacturer="Acme", model="Switch")
        .add_to_registry()
    )

    assert registry.match_green_power_entry(zigpy_gpd) is (entry if matches else None)


@pytest.mark.parametrize(
    ("src_id", "matches"),
    [
        (0x003FFFFF, False),
        (0x00400000, True),
        (0x004FFFFF, True),
        (0x00500000, False),
        (0x01700000, True),
        (0x0170FFFF, True),
        (0x01710000, False),
    ],
)
def test_green_power_quirk_builder_src_id_ranges(MockAppController, src_id, matches):
    """Test that SrcID ranges are inclusive and any one of them matches."""
    gpd = ZigpyGreenPowerDevice(
        MockAppController,
        application_id=ApplicationID.SrcID,
        src_id=SrcID(src_id),
    )
    gpd.device_id = DeviceID.OnOffSwitch

    registry = DeviceRegistry()

    entry = (
        GreenPowerQuirkBuilder(registry=registry)
        .src_id_range(0x00400000, 0x004FFFFF)
        .src_id_range(0x01700000, 0x0170FFFF)
        .friendly_name(manufacturer="Acme", model="Switch")
        .add_to_registry()
    )

    assert registry.match_green_power_entry(gpd) is (entry if matches else None)


@pytest.mark.parametrize(
    ("ieee", "matches"),
    [
        ("04:cd:15:00:11:22:33:44", True),
        ("04:cd:16:00:11:22:33:44", False),
        # The prefix is matched from the most significant byte
        ("44:33:22:11:00:15:cd:04", False),
    ],
)
def test_green_power_quirk_builder_ieee_prefixes(MockAppController, ieee, matches):
    """Test that an IEEE prefix only matches addresses starting with it."""
    gpd = ZigpyGreenPowerDevice(
        MockAppController,
        application_id=ApplicationID.IEEE,
        ieee=EUI64.convert(ieee),
    )

    registry = DeviceRegistry()

    entry = (
        GreenPowerQuirkBuilder(registry=registry)
        .ieee_prefix("04:cd:15")
        .friendly_name(manufacturer="Acme", model="Switch")
        .add_to_registry()
    )

    assert registry.match_green_power_entry(gpd) is (entry if matches else None)


def test_green_power_quirk_builder_src_id_range_or_ieee_prefix(
    MockAppController, zigpy_gpd
):
    """Test that a quirk with both identity criteria matches either kind of GPD."""
    ieee_gpd = ZigpyGreenPowerDevice(
        MockAppController,
        application_id=ApplicationID.IEEE,
        ieee=EUI64.convert("04:cd:15:00:11:22:33:44"),
    )

    registry = DeviceRegistry()

    entry = (
        GreenPowerQuirkBuilder(registry=registry)
        .src_id_range(0x01700000, 0x0170FFFF)
        .ieee_prefix("04:cd:15")
        .friendly_name(manufacturer="Acme", model="Switch")
        .add_to_registry()
    )

    assert registry.match_green_power_entry(zigpy_gpd) is entry
    assert registry.match_green_power_entry(ieee_gpd) is entry


@pytest.mark.parametrize("specific_first", [True, False])
def test_green_power_quirk_builder_specificity(zigpy_gpd, specific_first):
    """Test that a quirk with a SrcID range wins over a device ID-only quirk."""
    registry = DeviceRegistry()

    generic = (
        GreenPowerQuirkBuilder(registry=registry)
        .applies_to(device_id=DeviceID.OnOffSwitch)
        .friendly_name(manufacturer="Acme", model="Generic switch")
    )
    specific = (
        GreenPowerQuirkBuilder(registry=registry)
        .applies_to(device_id=DeviceID.OnOffSwitch)
        .src_id_range(0x01700000, 0x0170FFFF)
        .friendly_name(manufacturer="Acme", model="Specific switch")
    )

    if specific_first:
        specific_entry = specific.add_to_registry()
        generic.add_to_registry()
    else:
        generic.add_to_registry()
        specific_entry = specific.add_to_registry()

    assert registry.match_green_power_entry(zigpy_gpd) is specific_entry


def test_green_power_quirk_builder_duplicate_registration(zigpy_gpd):
    """Test that registering an identical quirk twice keeps a single entry."""
    registry = DeviceRegistry()

    def register():
        return (
            GreenPowerQuirkBuilder(registry=registry)
            .applies_to(device_id=DeviceID.OnOffSwitch)
            .adds_entity(
                CommandEvent,
                command_id=GPDCommandID.Toggle,
                event_type="toggle",
                unique_id_suffix="button",
                fallback_name="Button",
            )
            .friendly_name(manufacturer="Acme", model="Switch")
            .add_to_registry()
        )

    first = register()
    second = register()

    assert first == second
    assert list(registry) == [first]
    assert registry.match_green_power_entry(zigpy_gpd) is first


def test_green_power_quirk_without_entities(zigpy_gpd):
    """Test that a quirk adding no entities only renames the device."""
    registry = DeviceRegistry()

    entry = (
        GreenPowerQuirkBuilder(registry=registry)
        .applies_to(device_id=DeviceID.OnOffSwitch)
        .friendly_name(manufacturer="Acme", model="Switch")
        .add_to_registry()
    )

    zha_device = entry.zha_device_factory(zigpy_gpd, MagicMock())

    assert zha_device.quirk_metadata.added_entities == ()
    assert list(zha_device.discover_entities()) == []
    assert zha_device.name == "Acme Switch"


def test_green_power_quirk_entity_kwargs(zigpy_gpd):
    """Test that `adds_entity` passes its arguments through to the entity."""
    registry = DeviceRegistry()

    entry = (
        GreenPowerQuirkBuilder(registry=registry)
        .applies_to(device_id=DeviceID.OnOffSwitch)
        .adds_entity(
            CommandEvent,
            command_id=GPDCommandID.Toggle,
            event_type="toggle",
            unique_id_suffix="button_1",
            translation_key="button_numbered",
            translation_placeholders={"number": "1"},
            fallback_name="Button 1",
        )
        .friendly_name(manufacturer="Acme", model="Switch")
        .add_to_registry()
    )

    (added,) = entry.zha_device_factory.quirk_definition.added_entities
    assert added.entity_cls is CommandEvent
    assert added.endpoint_id is None
    assert added.cluster_id is None

    zha_device = entry.zha_device_factory(zigpy_gpd, MagicMock())
    (entity,) = zha_device.discover_entities()

    assert entity.device is zha_device
    assert entity.unique_id == f"{zigpy_gpd.ieee}-button_1"
    assert entity.translation_key == "button_numbered"
    assert entity.translation_placeholders == {"number": "1"}
    assert entity.fallback_name == "Button 1"
