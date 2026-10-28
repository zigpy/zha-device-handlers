"""The declarative (GreenPowerQuirkBuilder) authoring API for Green Power devices."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import inspect
import pathlib
from types import FrameType
from typing import TYPE_CHECKING, Any, Self

# `discovery` must be imported before `zha.zigbee.device`: the platform modules
# it loads participate in an import cycle with the device module and cannot be
# loaded while `zha.zigbee.device` is only partially initialized.
from zha.application import discovery  # noqa: F401
from zha.application.platforms import PlatformEntity, ZclPlatformEntity
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
from zigpy.zcl import ClusterType
from zigpy.zgp.types import DeviceID, SrcID

from zhaquirks.builder.device import create_added_entities
from zhaquirks.builder.metadata import AddedEntityMetadata

if TYPE_CHECKING:
    from zha.application.gateway import Gateway


@dataclass(frozen=True)
class GreenPowerQuirkDefinition:
    """ZHA-level metadata for a Green Power quirk."""

    friendly_manufacturer: str
    friendly_model: str
    added_entities: tuple[AddedEntityMetadata, ...] = ()


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

    def discover_entities(self) -> Iterator[PlatformEntity]:
        """Yield the quirk's entities."""
        yield from super().discover_entities()

        yield from create_added_entities(self, self._quirk_definition.added_entities)

    def _resolve_manufacturer(self) -> str:
        return self._quirk_definition.friendly_manufacturer

    def _resolve_model(self) -> str:
        return self._quirk_definition.friendly_model


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
        self.added_entities: list[AddedEntityMetadata] = []
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

    def adds_entity(
        self,
        entity_cls: type[PlatformEntity],
        *,
        unique_id_suffix: str,
        **kwargs: Any,
    ) -> Self:
        """Add an entity bound to the device, created with `kwargs`."""
        if issubclass(entity_cls, ZclPlatformEntity):
            raise TypeError(
                f"{entity_cls!r} needs a ZCL cluster, Green Power devices have none"
            )

        if "unique_id" in kwargs:
            raise ValueError(
                "The quirk sets the unique ID base, use `unique_id_suffix` instead"
            )

        if any(
            added.kwargs["unique_id_suffix"] == unique_id_suffix
            for added in self.added_entities
        ):
            raise ValueError(f"Duplicate unique_id_suffix: {unique_id_suffix!r}")

        self.added_entities.append(
            AddedEntityMetadata(
                entity_cls=entity_cls,
                endpoint_id=None,
                cluster_id=None,
                cluster_type=ClusterType.Server,
                kwargs={**kwargs, "unique_id_suffix": unique_id_suffix},
            )
        )
        return self

    def device_class(self, custom_device_class: type[QuirkGreenPowerDevice]) -> Self:
        """Set a custom ZHA device class."""
        if not issubclass(custom_device_class, QuirkGreenPowerDevice):
            raise TypeError(
                f"{custom_device_class} is not a subclass of QuirkGreenPowerDevice"
            )

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

        if self.friendly_manufacturer is None or self.friendly_model is None:
            raise ValueError("A Green Power quirk must have a friendly name")

        quirk_definition = GreenPowerQuirkDefinition(
            friendly_manufacturer=self.friendly_manufacturer,
            friendly_model=self.friendly_model,
            added_entities=tuple(self.added_entities),
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
