"""Quirks v2 metadata model.

The declarative metadata produced by `zhaquirks.builder.QuirkBuilder`: exposed
entities, default-entity changes, alerts and naming, aggregated into a
`QuirkDefinition` carried by the quirk's `QuirkRegistryEntry` and exposed to ZHA
by `QuirkV2Device`. This model is internal to the quirks layer; ZHA's entity
classes take plain keyword arguments and know nothing about it.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import Any

import attrs
from frozendict import frozendict
from zha.application import EntityPlatform, EntityType
from zha.application.platforms.binary_sensor.device_class import BinarySensorDeviceClass
from zha.application.platforms.number.device_class import NumberDeviceClass
from zha.application.platforms.sensor.device_class import (
    SensorDeviceClass,
    SensorStateClass,
)
from zigpy.zcl import ClusterType

# pylint: disable=too-many-instance-attributes


@attrs.define(frozen=True, kw_only=True, repr=True)
class ReportingConfig:
    """Reporting config for an entity attribute."""

    min_interval: int
    max_interval: int
    reportable_change: int


@attrs.define(frozen=True, kw_only=True, repr=True)
class EntityMetadata:
    """Metadata for an exposed entity."""

    entity_platform: EntityPlatform = attrs.field()
    entity_type: EntityType = attrs.field()
    cluster_id: int = attrs.field()
    endpoint_id: int = attrs.field(default=1)
    cluster_type: ClusterType = attrs.field(default=ClusterType.Server)
    initially_disabled: bool = attrs.field(default=False)
    attribute_initialized_from_cache: bool = attrs.field(default=True)
    unique_id_suffix: str | None = attrs.field(default=None)
    translation_key: str | None = attrs.field(default=None)
    translation_placeholders: frozendict[str, str] = attrs.field(
        factory=frozendict, converter=frozendict
    )
    fallback_name: str = attrs.field(validator=attrs.validators.instance_of(str))
    primary: bool | None = attrs.field(default=None)

    def __attrs_post_init__(self) -> None:
        """Validate the entity metadata."""
        has_device_class: bool = getattr(self, "device_class", None) is not None
        if self.translation_key is None and not has_device_class:
            raise ValueError(
                f"EntityMetadata must have a translation_key or device_class: {self}"
            )

    @property
    def resolved_unique_id_suffix(self) -> str | None:
        """Return the unique_id suffix, falling back to attribute/command name.

        ZHA's entity base no longer derives the suffix; the quirks layer resolves
        it here so the unique_id is byte-identical to the legacy behavior.
        """
        if self.unique_id_suffix is not None:
            return self.unique_id_suffix
        attribute_name = getattr(self, "attribute_name", None)
        if attribute_name is not None:
            return attribute_name
        return getattr(self, "command_name", None)


@attrs.define(frozen=True, kw_only=True, repr=True)
class ZCLEnumMetadata(EntityMetadata):
    """Metadata for exposed ZCL enum based entity."""

    enum: type[Enum] = attrs.field()
    attribute_name: str = attrs.field()
    reporting_config: ReportingConfig | None = attrs.field(default=None)


@attrs.define(frozen=True, kw_only=True, repr=True)
class ZCLSensorMetadata(EntityMetadata):
    """Metadata for exposed ZCL attribute based sensor entity."""

    attribute_name: str | None = attrs.field(default=None)
    attribute_converter: Callable[[Any], Any] | None = attrs.field(default=None)
    reporting_config: ReportingConfig | None = attrs.field(default=None)
    divisor: int | None = attrs.field(default=None)
    multiplier: int | None = attrs.field(default=None)
    suggested_display_precision: int | None = attrs.field(default=None)
    unit: str | None = attrs.field(default=None)
    device_class: SensorDeviceClass | None = attrs.field(default=None)
    state_class: SensorStateClass | None = attrs.field(default=None)


@attrs.define(frozen=True, kw_only=True, repr=True)
class SwitchMetadata(EntityMetadata):
    """Metadata for exposed switch entity."""

    attribute_name: str = attrs.field()
    reporting_config: ReportingConfig | None = attrs.field(default=None)
    force_inverted: bool = attrs.field(default=False)
    invert_attribute_name: str | None = attrs.field(default=None)
    off_value: int = attrs.field(default=0)
    on_value: int = attrs.field(default=1)


@attrs.define(frozen=True, kw_only=True, repr=True)
class NumberMetadata(EntityMetadata):
    """Metadata for exposed number entity."""

    attribute_name: str = attrs.field()
    reporting_config: ReportingConfig | None = attrs.field(default=None)
    min: float | None = attrs.field(default=None)
    max: float | None = attrs.field(default=None)
    step: float | None = attrs.field(default=None)
    unit: str | None = attrs.field(default=None)
    mode: str | None = attrs.field(default=None)
    multiplier: float | None = attrs.field(default=None)
    device_class: NumberDeviceClass | None = attrs.field(default=None)


@attrs.define(frozen=True, kw_only=True, repr=True)
class BinarySensorMetadata(EntityMetadata):
    """Metadata for exposed binary sensor entity."""

    attribute_name: str = attrs.field()
    attribute_converter: Callable[[Any], Any] | None = attrs.field(default=None)
    reporting_config: ReportingConfig | None = attrs.field(default=None)
    device_class: BinarySensorDeviceClass | None = attrs.field(default=None)


@attrs.define(frozen=True, kw_only=True, repr=True)
class WriteAttributeButtonMetadata(EntityMetadata):
    """Metadata for exposed button entity that writes an attribute when pressed."""

    attribute_name: str = attrs.field()
    attribute_value: int = attrs.field()


@attrs.define(frozen=True, kw_only=True, repr=True)
class ZCLCommandButtonMetadata(EntityMetadata):
    """Metadata for exposed button entity that executes a ZCL command when pressed."""

    command_name: str = attrs.field()
    args: tuple = attrs.field(default=())
    kwargs: frozendict[str, Any] = attrs.field(factory=frozendict, converter=frozendict)


@attrs.define(frozen=True, kw_only=True, repr=True)
class FriendlyNameMetadata:
    """Metadata to rename a device."""

    model: str = attrs.field()
    manufacturer: str = attrs.field()


@attrs.define(frozen=True, kw_only=True, repr=True)
class ExposesFeatureMetadata:
    """Metadata for an exposed feature to match against in ZHA."""

    feature: str = attrs.field()
    config: frozendict[str, Any] = attrs.field(factory=frozendict, converter=frozendict)


class DeviceAlertLevel(Enum):
    """Device alert level."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@attrs.define(frozen=True, kw_only=True, repr=True)
class DeviceAlertMetadata:
    """Metadata for device-specific alerts."""

    level: DeviceAlertLevel = attrs.field(converter=DeviceAlertLevel)
    message: str = attrs.field()


@attrs.define(frozen=True, kw_only=True, repr=True)
class PreventDefaultEntityCreationMetadata:
    """Metadata to prevent the default creation of an entity."""

    endpoint_id: int | None = attrs.field()
    cluster_id: int | None = attrs.field()
    cluster_type: ClusterType | None = attrs.field()
    unique_id_suffix: str | None = attrs.field()
    function: Callable[[Any], bool] | None = attrs.field()


@attrs.define(frozen=True, kw_only=True, repr=True)
class ChangedEntityMetadata:
    """Metadata to change entity metadata for matching entities."""

    endpoint_id: int | None = attrs.field()
    cluster_id: int | None = attrs.field()
    cluster_type: ClusterType | None = attrs.field()
    unique_id_suffix: str | None = attrs.field()
    function: Callable[[Any], bool] | None = attrs.field()
    # Entity metadata changes
    new_primary: bool | None = attrs.field(default=None)
    new_unique_id: str | None = attrs.field(default=None)
    new_translation_key: str | None = attrs.field(default=None)
    new_translation_placeholders: frozendict[str, str] | None = attrs.field(
        default=None, converter=lambda d: None if d is None else frozendict(d)
    )
    new_device_class: (
        BinarySensorDeviceClass | NumberDeviceClass | SensorDeviceClass | None
    ) = attrs.field(default=None)
    new_state_class: SensorStateClass | None = attrs.field(default=None)
    new_entity_category: EntityType | None = attrs.field(default=None)
    new_entity_registry_enabled_default: bool | None = attrs.field(default=None)
    new_fallback_name: str | None = attrs.field(default=None)


def recursive_freeze(obj: Any) -> Any:
    """Recursively convert mutable collections to immutable ones."""
    if isinstance(obj, dict):
        return frozendict({k: recursive_freeze(v) for k, v in obj.items()})
    if isinstance(obj, tuple | list | set):
        return tuple(recursive_freeze(v) for v in obj)
    return obj


@attrs.define(frozen=True, kw_only=True, repr=True)
class QuirkDefinition:
    """ZHA-level metadata of a quirk.

    Everything a quirk expresses about the ZHA device model: entities,
    automation triggers, alerts and naming. Zigbee-level modifications
    (`zigpy_transforms`) and provenance (`source`) live on the quirk's
    `zha.quirks.QuirkRegistryEntry`, not here.
    """

    friendly_name: FriendlyNameMetadata | None = attrs.field(default=None)
    exposes_features: tuple[ExposesFeatureMetadata, ...] = attrs.field(factory=tuple)
    device_alerts: tuple[DeviceAlertMetadata, ...] = attrs.field(factory=tuple)
    disabled_default_entities: tuple[PreventDefaultEntityCreationMetadata, ...] = (
        attrs.field(factory=tuple)
    )
    changed_entity_metadata: tuple[ChangedEntityMetadata, ...] = attrs.field(
        factory=tuple
    )
    entity_metadata: tuple[EntityMetadata, ...] = attrs.field(factory=tuple)
    device_automation_triggers: frozendict[tuple[str, str], frozendict[str, str]] = (
        attrs.field(factory=frozendict, converter=recursive_freeze)
    )
    skip_configuration: bool = attrs.field(default=False)
