"""The declarative (GreenPowerQuirkBuilder) authoring API for Green Power devices."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
import inspect
import pathlib
from types import FrameType
from typing import TYPE_CHECKING, Any, Self

# `discovery` must be imported before `zha.zigbee.device`: the platform modules
# it loads participate in an import cycle with the device module and cannot be
# loaded while `zha.zigbee.device` is only partially initialized.
from zha.application import discovery  # noqa: F401
from zha.application.platforms import BaseEntity
from zha.application.platforms.event import BaseEvent
from zha.application.platforms.event.const import EventDeviceClass
from zha.quirks import (
    DEVICE_REGISTRY,
    DeviceRegistry,
    GreenPowerDeviceMatch,
    GreenPowerFilterType,
    GreenPowerQuirkRegistryEntry,
    QuirkSource,
)
from zha.zigbee.device import GreenPowerDevice
import zigpy.device
from zigpy.device import GreenPowerCommandReceived
from zigpy.zgp.types import DeviceID, GPDCommandID, SrcID

if TYPE_CHECKING:
    from zha.application.gateway import Gateway


@dataclass(frozen=True)
class GreenPowerEventTrigger:
    """A GPD command, with optional payload field values, firing an event type."""

    command_id: GPDCommandID
    params: Mapping[str, Any] | tuple[tuple[str, Any], ...] = ()

    def __post_init__(self) -> None:
        """Freeze the payload field constraints."""
        if not isinstance(self.params, tuple):
            object.__setattr__(self, "params", tuple(self.params.items()))

    def matches(self, event: GreenPowerCommandReceived) -> bool:
        """Return True if the received GPD command fires this trigger."""
        if event.command_id != self.command_id:
            return False

        assert isinstance(self.params, tuple)
        return all(
            event.command is not None and getattr(event.command, name) == value
            for name, value in self.params
        )


@dataclass(frozen=True)
class GreenPowerEventMetadata:
    """Metadata for an event entity fired by GPD commands."""

    event_types: tuple[tuple[str, GreenPowerEventTrigger], ...]
    fallback_name: str
    translation_key: str | None = None
    device_class: EventDeviceClass | None = None
    unique_id_suffix: str | None = None
    primary: bool = False
    initially_disabled: bool = False
    # A quirk needing more than trigger matching provides its own entity class
    entity_class: type[GreenPowerEventEntity] | None = None


@dataclass(frozen=True)
class GreenPowerQuirkDefinition:
    """ZHA-level metadata for a Green Power quirk."""

    friendly_manufacturer: str | None = None
    friendly_model: str | None = None
    events: tuple[GreenPowerEventMetadata, ...] = ()


class GreenPowerEventEntity(BaseEvent):
    """Event entity fired by GPD commands."""

    def __init__(
        self,
        device: GreenPowerDevice,
        *,
        event_metadata: GreenPowerEventMetadata,
    ) -> None:
        """Initialize the event entity."""
        self._event_metadata = event_metadata
        self._attr_event_types = [name for name, _ in event_metadata.event_types]
        self._attr_device_class = event_metadata.device_class

        super().__init__(
            device,
            unique_id=str(device.ieee),
            from_quirk=True,
            fallback_name=event_metadata.fallback_name,
            translation_key=event_metadata.translation_key,
            unique_id_suffix=event_metadata.unique_id_suffix,
            primary=event_metadata.primary,
            initially_disabled=event_metadata.initially_disabled,
        )

        self._on_remove_callbacks.append(
            device.device.on_event(
                GreenPowerCommandReceived.event_type,
                self._handle_gp_command_received,
            )
        )

    def _handle_gp_command_received(self, event: GreenPowerCommandReceived) -> None:
        """Fire the event types triggered by a received GPD command."""
        for event_type, trigger in self._event_metadata.event_types:
            if trigger.matches(event):
                self._trigger_event(
                    event_type,
                    event.command.as_dict() if event.command is not None else {},
                )


class QuirkGreenPowerDevice(GreenPowerDevice):
    """Base ZHA device for GreenPowerQuirkBuilder."""

    def __init__(
        self,
        zigpy_device: zigpy.device.GreenPowerDevice,
        gateway: Gateway,
        *,
        quirk_definition: GreenPowerQuirkDefinition,
    ) -> None:
        """Initialize the quirk device."""
        self._quirk_definition = quirk_definition
        super().__init__(zigpy_device, gateway)

    @property
    def quirk_metadata(self) -> GreenPowerQuirkDefinition:
        """Return the ZHA-level quirk metadata for this device."""
        return self._quirk_definition

    def discover_entities(self) -> Iterator[BaseEntity]:
        """Yield the quirk's event entities."""
        yield from super().discover_entities()

        for event_metadata in self._quirk_definition.events:
            entity_class = event_metadata.entity_class or GreenPowerEventEntity

            yield entity_class(self, event_metadata=event_metadata)

    def _resolve_manufacturer(self) -> str:
        if self._quirk_definition.friendly_manufacturer is not None:
            return self._quirk_definition.friendly_manufacturer
        return super()._resolve_manufacturer()

    def _resolve_model(self) -> str:
        if self._quirk_definition.friendly_model is not None:
            return self._quirk_definition.friendly_model
        return super()._resolve_model()


@dataclass(frozen=True)
class GreenPowerQuirkFactory:
    """Registry-entry factory building a `QuirkGreenPowerDevice` bound to its definition."""

    base: type[QuirkGreenPowerDevice]
    quirk_definition: GreenPowerQuirkDefinition

    def __call__(
        self, zigpy_device: zigpy.device.GreenPowerDevice, gateway: Gateway
    ) -> QuirkGreenPowerDevice:
        """Build the bound `QuirkGreenPowerDevice` for a resolved zigpy device."""
        return self.base(zigpy_device, gateway, quirk_definition=self.quirk_definition)


class GreenPowerQuirkBuilder:
    """Builder compiling a declarative Green Power quirk into a registry entry."""

    def __init__(self, registry: DeviceRegistry = DEVICE_REGISTRY) -> None:
        """Initialize the quirk builder."""
        self.registry: DeviceRegistry = registry
        self.device_id: DeviceID | None = None
        self.manufacturer_id: int | None = None
        self.model_id: int | None = None
        self.src_id_ranges: list[tuple[SrcID, SrcID]] = []
        self.ieee_prefixes: list[bytes] = []
        self.filters: list[GreenPowerFilterType] = []
        self.friendly_manufacturer: str | None = None
        self.friendly_model: str | None = None
        self.events: list[GreenPowerEventMetadata] = []
        self.custom_device_class: type[QuirkGreenPowerDevice] | None = None

        current_frame: FrameType = inspect.currentframe()
        caller: FrameType = current_frame.f_back
        self.quirk_file = pathlib.Path(caller.f_code.co_filename)
        self.quirk_file_line = caller.f_lineno
        self.quirk_module: str = caller.f_globals["__name__"]

    def applies_to(
        self,
        *,
        device_id: DeviceID | int | None = None,
        manufacturer_id: int | None = None,
        model_id: int | None = None,
    ) -> Self:
        """Match the GPD's commissioning identity fields."""
        if device_id is None and manufacturer_id is None and model_id is None:
            raise ValueError(
                "At least one of device_id, manufacturer_id, or model_id must be"
                " specified"
            )

        if device_id is not None:
            self.device_id = DeviceID(device_id)
        if manufacturer_id is not None:
            self.manufacturer_id = manufacturer_id
        if model_id is not None:
            self.model_id = model_id

        return self

    def src_id_range(self, lower: int, upper: int) -> Self:
        """Match SrcIDs within `[lower, upper]`: vendors allocate SrcID blocks."""
        self.src_id_ranges.append((SrcID(lower), SrcID(upper)))
        return self

    def ieee_prefix(self, prefix: str) -> Self:
        """Match IEEE-addressed GPDs whose address begins with `prefix` ("04:cd:15")."""
        self.ieee_prefixes.append(bytes(int(octet, 16) for octet in prefix.split(":")))
        return self

    def filter(self, filter_function: GreenPowerFilterType) -> Self:
        """Add a filter and return self.

        The filter function should take a single argument, a
        `zigpy.device.GreenPowerDevice` instance, and return a boolean if the
        condition the filter is testing passes.
        """
        self.filters.append(filter_function)
        return self

    def friendly_name(self, *, manufacturer: str, model: str) -> Self:
        """Override the device name displayed in HA."""
        self.friendly_manufacturer = manufacturer
        self.friendly_model = model
        return self

    def event(
        self,
        event_types: Mapping[str, GreenPowerEventTrigger],
        *,
        device_class: EventDeviceClass | None = None,
        unique_id_suffix: str | None = None,
        primary: bool = False,
        initially_disabled: bool = False,
        translation_key: str | None = None,
        fallback_name: str,
        entity_class: type[GreenPowerEventEntity] | None = None,
    ) -> Self:
        """Add an event entity fired by the given GPD commands."""
        if translation_key is None and device_class is None:
            raise ValueError(
                "A translation key must be provided when no device class is set"
            )

        if primary and any(metadata.primary for metadata in self.events):
            raise ValueError("Only one primary entity can be defined per device")

        if any(
            metadata.unique_id_suffix == unique_id_suffix for metadata in self.events
        ):
            raise ValueError(
                f"An event entity with unique_id_suffix {unique_id_suffix!r} is"
                " already defined"
            )

        self.events.append(
            GreenPowerEventMetadata(
                event_types=tuple(event_types.items()),
                fallback_name=fallback_name,
                translation_key=translation_key,
                device_class=device_class,
                unique_id_suffix=unique_id_suffix,
                primary=primary,
                initially_disabled=initially_disabled,
                entity_class=entity_class,
            )
        )
        return self

    def device_class(self, custom_device_class: type[QuirkGreenPowerDevice]) -> Self:
        """Set a custom ZHA device class."""
        assert issubclass(custom_device_class, QuirkGreenPowerDevice)
        self.custom_device_class = custom_device_class
        return self

    def add_to_registry(
        self, registry: DeviceRegistry | None = None
    ) -> GreenPowerQuirkRegistryEntry:
        """Compile the quirk into a `GreenPowerQuirkRegistryEntry` and register it."""
        device_match = GreenPowerDeviceMatch(
            device_id=self.device_id,
            manufacturer_id=self.manufacturer_id,
            model_id=self.model_id,
            src_id_ranges=tuple(self.src_id_ranges),
            ieee_prefixes=tuple(self.ieee_prefixes),
            filters=tuple(self.filters),
        )

        if device_match == GreenPowerDeviceMatch():
            raise ValueError(
                "At least one matching criterion must be specified for a Green Power"
                " quirk"
            )

        quirk_definition = GreenPowerQuirkDefinition(
            friendly_manufacturer=self.friendly_manufacturer,
            friendly_model=self.friendly_model,
            events=tuple(self.events),
        )

        base = (
            self.custom_device_class
            if self.custom_device_class
            else QuirkGreenPowerDevice
        )
        zha_device_factory = GreenPowerQuirkFactory(base, quirk_definition)

        entry = GreenPowerQuirkRegistryEntry(
            device_match=device_match,
            zha_device_factory=zha_device_factory,
            source=QuirkSource(
                module=self.quirk_module,
                file=str(self.quirk_file),
                line=self.quirk_file_line,
                label=f"({self.friendly_manufacturer} / {self.friendly_model})",
            ),
        )

        (registry or self.registry).register(entry)

        return entry
