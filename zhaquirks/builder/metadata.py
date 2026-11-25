"""Quirks v2 metadata model.

The declarative metadata produced by `zhaquirks.builder.QuirkBuilder`: exposed
entities, default-entity changes, alerts and naming, aggregated into a
`QuirkDefinition` carried by the quirk's `QuirkRegistryEntry` and exposed to ZHA
by `QuirkV2Device`. This model is internal to the quirks layer; ZHA's entity
classes take plain keyword arguments and know nothing about it.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from enum import Enum
from typing import Any

import attrs
from frozendict import frozendict
from zha.application import EntityPlatform, EntityType
from zha.application.platforms import PlatformEntity, ZclPlatformEntity
from zha.application.platforms.binary_sensor.device_class import BinarySensorDeviceClass
from zha.application.platforms.event import ZhaEventRotaryMatch
from zha.application.platforms.event.const import (
    ButtonEventType,
    RotaryDirection,
    RotaryEventType,
)
from zha.application.platforms.number.device_class import NumberDeviceClass
from zha.application.platforms.sensor.device_class import (
    SensorDeviceClass,
    SensorStateClass,
)
from zigpy.typing import UNDEFINED, UndefinedType
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
    # The child device the entity belongs to, `None` for the main device. By default
    # it belongs to the child device defined for its endpoint, if any.
    child_device_id: str | None | UndefinedType = attrs.field(
        default=UNDEFINED,
        validator=attrs.validators.instance_of((str, type(None), UndefinedType)),
    )

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


def recursive_freeze(obj: Any) -> Any:
    """Recursively convert mutable collections to immutable ones."""
    if isinstance(obj, Mapping):
        return frozendict({k: recursive_freeze(v) for k, v in obj.items()})
    if isinstance(obj, tuple | list | set):
        return tuple(recursive_freeze(v) for v in obj)
    return obj


# The `zha_event` data keys an event can match: ZHA sends these for a cluster
# command and for a quirk's `zha_send_event`. Its `unique_id` is left out: it holds
# the device's IEEE address, so a quirk can't match it.
ZHA_EVENT_DATA_KEYS = frozenset(
    {"command", "cluster_id", "endpoint_id", "args", "params"}
)


def _validate_zha_event_data(event_data: Any, source: object) -> None:
    """Validate that event data can match a `zha_event`."""
    if not isinstance(event_data, Mapping):
        raise TypeError(
            f"Event data is a mapping of zha_event keys, not {event_data!r}: {source}"
        )

    if unknown := set(event_data) - ZHA_EVENT_DATA_KEYS:
        raise ValueError(
            f"Event data has keys a zha_event does not have"
            f" ({', '.join(sorted(map(repr, unknown)))}), so it never matches: {source}"
        )

    if any(_has_empty_mapping(value) for value in event_data.values()):
        raise ValueError(
            f"Event data with an empty mapping matches any mapping in its place: {source}"
        )


def _has_empty_mapping(value: Any) -> bool:
    if isinstance(value, Mapping):
        return not value or any(map(_has_empty_mapping, value.values()))

    if isinstance(value, list | tuple):
        return any(map(_has_empty_mapping, value))

    return False


def _convert_trigger(trigger: Any) -> Any:
    """Return a device automation trigger key as a tuple, if it is a sequence."""
    if isinstance(trigger, Iterable) and not isinstance(trigger, str):
        return tuple(trigger)
    return trigger


def _validate_event_source(
    trigger: tuple[str, str] | None,
    event_data: Mapping[str, Any] | None,
    source: ButtonEvent | RotaryEvent,
) -> None:
    """Validate the `zha_event` an event fires for: a trigger or event data."""
    if (trigger is None) == (event_data is None):
        raise ValueError(f"An event needs either a trigger or event data: {source}")

    if trigger is not None and (
        not isinstance(trigger, tuple)
        or len(trigger) != 2
        or not all(isinstance(part, str) for part in trigger)
    ):
        raise ValueError(f"A trigger is a (type, subtype) pair of strings: {trigger!r}")

    if event_data is not None:
        _validate_zha_event_data(event_data, source)

        if not event_data:
            raise ValueError(f"Empty event data matches every zha_event: {source}")


@attrs.define(frozen=True, kw_only=True, repr=True)
class ButtonEvent:
    """An event type a button event entity fires, and the `zha_event` firing it.

    The `zha_event` is given either as the key of one of the quirk's device
    automation triggers, so the event fires for the `zha_event`s that trigger's data
    matches, or as `event_data` matched like the data of such a trigger.
    """

    event_type: ButtonEventType = attrs.field(converter=ButtonEventType)
    trigger: tuple[str, str] | None = attrs.field(
        default=None, converter=_convert_trigger
    )
    event_data: frozendict[str, Any] | None = attrs.field(
        default=None, converter=lambda d: None if d is None else recursive_freeze(d)
    )
    # The number of presses of a `multi_press`
    press_count: int | None = attrs.field(default=None)
    # The device repeats this `long_press_start` while the button is held
    repeats: bool = attrs.field(default=False)
    # Only match while the button is held, to classify a `long_press_end` the device
    # does not tell apart, by button or from a short press
    while_held: bool = attrs.field(default=False)

    def __attrs_post_init__(self) -> None:
        """Validate the button event."""
        _validate_event_source(self.trigger, self.event_data, self)

        if (self.event_type == ButtonEventType.MULTI_PRESS) != (
            self.press_count is not None
        ):
            raise ValueError(
                f"A press count is required for '{ButtonEventType.MULTI_PRESS}' and"
                f" only allowed there: {self}"
            )

        if self.repeats and self.event_type != ButtonEventType.LONG_PRESS_START:
            raise ValueError(
                f"Only '{ButtonEventType.LONG_PRESS_START}' can repeat: {self}"
            )

        if self.while_held and self.event_type != ButtonEventType.LONG_PRESS_END:
            raise ValueError(
                f"Only '{ButtonEventType.LONG_PRESS_END}' can match while held: {self}"
            )

        if self.press_count is not None and (
            isinstance(self.press_count, bool)
            or not isinstance(self.press_count, int)
            or self.press_count < 2
        ):
            raise ValueError(f"A multi press needs at least two presses: {self}")


def _convert_rotary_event_type(event_type: Any) -> Any:
    """Return a standard rotary event type as a `RotaryEventType`."""
    return RotaryEventType(event_type) if event_type in RotaryEventType else event_type


def _convert_rotary_direction(direction: Any) -> Any:
    """Return a valid direction as a `RotaryDirection`."""
    return RotaryDirection(direction) if direction in RotaryDirection else direction


@attrs.define(frozen=True, kw_only=True, repr=True)
class RotaryEvent:
    """An event type a rotary event entity fires, and the `zha_event` firing it.

    The `zha_event` is given like for a `ButtonEvent`. The event type is a
    `RotaryEventType` or an integration-specific type. The direction is a constant
    of the event, as devices report each direction with their own command or
    parameter. Other event data is constant (`event_attributes`) or taken from the
    `zha_event` (`event_attributes_from_data`, the path of keys and indexes to the
    value). The rules are those of ZHA's `ZhaEventRotaryMatch`.
    """

    event_type: RotaryEventType | str = attrs.field(
        converter=_convert_rotary_event_type
    )
    trigger: tuple[str, str] | None = attrs.field(
        default=None, converter=_convert_trigger
    )
    event_data: frozendict[str, Any] | None = attrs.field(
        default=None, converter=lambda d: None if d is None else recursive_freeze(d)
    )
    # Required for `rotation` and `rotation_start`
    direction: RotaryDirection | None = attrs.field(
        default=None, converter=_convert_rotary_direction
    )
    event_attributes: frozendict[str, Any] = attrs.field(
        factory=frozendict, converter=recursive_freeze
    )
    event_attributes_from_data: frozendict[str, tuple[str | int, ...]] = attrs.field(
        factory=frozendict, converter=recursive_freeze
    )

    def __attrs_post_init__(self) -> None:
        """Validate the rotary event."""
        _validate_event_source(self.trigger, self.event_data, self)

        for name in ("event_attributes", "event_attributes_from_data"):
            if not isinstance(getattr(self, name), Mapping):
                raise TypeError(f"{name} is a mapping of event data names: {self}")

        # ZHA validates the rest when it creates the match. A trigger's data is only
        # known with the quirk, so validate the rest with the event's own data or a
        # stand-in for the trigger's
        try:
            ZhaEventRotaryMatch(
                event_type=self.event_type,
                event_data=self.event_data or {"command": "trigger"},
                direction=self.direction,
                event_attributes=self.event_attributes,
                event_attributes_from_data=self.event_attributes_from_data,
            )
        except ValueError as exc:
            raise ValueError(f"{exc}: {self}") from exc


@attrs.define(frozen=True, kw_only=True, repr=True)
class EventEntityMetadata[EventT: (ButtonEvent, RotaryEvent)](EntityMetadata):
    """Metadata for an exposed event entity firing events for `zha_event`s."""

    entity_platform: EntityPlatform = attrs.field(default=EntityPlatform.EVENT)
    entity_type: EntityType = attrs.field(default=EntityType.STANDARD)
    # Required: most controls are on client clusters, and there is no attribute or
    # command name to derive a unique ID suffix from
    cluster_type: ClusterType = attrs.field(converter=ClusterType)
    unique_id_suffix: str = attrs.field(
        validator=[attrs.validators.instance_of(str), attrs.validators.min_len(1)]
    )
    events: tuple[EventT, ...] = attrs.field(converter=tuple)

    def __attrs_post_init__(self) -> None:
        """Validate the event entity metadata."""
        super().__attrs_post_init__()

        if not self.events:
            raise ValueError(f"An event entity needs events: {self}")


@attrs.define(frozen=True, kw_only=True, repr=True)
class ButtonEventMetadata(EventEntityMetadata[ButtonEvent]):
    """Metadata for an exposed button event entity.

    v1 quirks expose these in their `button_event_entities` class attribute.
    """

    def __attrs_post_init__(self) -> None:
        """Validate the button event metadata."""
        super().__attrs_post_init__()

        event_types = {event.event_type for event in self.events}
        if (
            ButtonEventType.MULTI_PRESS in event_types
            and ButtonEventType.SINGLE_PRESS not in event_types
        ):
            raise ValueError(
                f"'{ButtonEventType.MULTI_PRESS}' is only allowed together with"
                f" '{ButtonEventType.SINGLE_PRESS}': {self}"
            )

        # A repeated hold is only fired again after another event of the entity
        if any(event.repeats for event in self.events) and event_types == {
            ButtonEventType.LONG_PRESS_START
        }:
            raise ValueError(
                f"A repeated '{ButtonEventType.LONG_PRESS_START}' needs another event"
                f" type ending the hold: {self}"
            )

        if (
            any(event.while_held for event in self.events)
            and ButtonEventType.LONG_PRESS_START not in event_types
        ):
            raise ValueError(
                f"Matching while held needs a '{ButtonEventType.LONG_PRESS_START}':"
                f" {self}"
            )


@attrs.define(frozen=True, kw_only=True, repr=True)
class RotaryEventMetadata(EventEntityMetadata[RotaryEvent]):
    """Metadata for an exposed rotary event entity.

    Rotary event entities have no device class, so they need a translation key.
    v1 quirks expose these in their `rotary_event_entities` class attribute.
    """

    def __attrs_post_init__(self) -> None:
        """Validate the rotary event metadata."""
        super().__attrs_post_init__()

        if not {RotaryEventType.ROTATION, RotaryEventType.ROTATION_START} & {
            event.event_type for event in self.events
        }:
            raise ValueError(
                f"A rotary event entity needs '{RotaryEventType.ROTATION}' or"
                f" '{RotaryEventType.ROTATION_START}': {self}"
            )


def validate_event_triggers(
    entity_metadata: EventEntityMetadata,
    device_automation_triggers: Mapping[tuple[str, str], Any],
) -> None:
    """Validate that an event entity only uses triggers the quirk defines."""
    for event in entity_metadata.events:
        if event.trigger is None:
            continue

        if event.trigger not in device_automation_triggers:
            raise ValueError(
                f"Event {event} of {entity_metadata.unique_id_suffix!r} uses a"
                " device automation trigger the quirk does not define"
            )

        if not device_automation_triggers[event.trigger]:
            raise ValueError(
                f"Event {event} of {entity_metadata.unique_id_suffix!r} uses a"
                " device automation trigger without data, which matches every"
                " zha_event"
            )

        _validate_zha_event_data(
            device_automation_triggers[event.trigger],
            f"trigger {event.trigger} of {entity_metadata.unique_id_suffix!r}",
        )


def _is_sequence(value: Any) -> bool:
    return isinstance(value, list | tuple)


def _event_data_covers(expected: Mapping[str, Any], other: Mapping[str, Any]) -> bool:
    """Return whether every `zha_event` matching `other` also matches `expected`.

    This follows ZHA's matching of event data: every expected key with an equal
    value, nested mappings as a subset, sequences item by item.
    """
    return all(
        key in other and _event_value_covers(value, other[key])
        for key, value in expected.items()
    )


def _event_value_covers(expected: Any, other: Any) -> bool:
    if isinstance(expected, Mapping):
        return isinstance(other, Mapping) and _event_data_covers(expected, other)

    if _is_sequence(expected) and _is_sequence(other):
        return len(expected) == len(other) and all(
            map(_event_value_covers, expected, other)
        )

    return bool(expected == other)


def _event_data_overlap(first: Mapping[str, Any], second: Mapping[str, Any]) -> bool:
    """Return whether a `zha_event` can match both event data."""
    return all(
        _event_value_overlap(first[key], second[key])
        for key in first.keys() & second.keys()
    )


def _event_value_overlap(first: Any, second: Any) -> bool:
    if isinstance(first, Mapping) and isinstance(second, Mapping):
        return _event_data_overlap(first, second)

    if _is_sequence(first) and _is_sequence(second):
        return len(first) == len(second) and all(
            map(_event_value_overlap, first, second)
        )

    if isinstance(first, Mapping) or isinstance(second, Mapping):
        return False

    return bool(first == second)


def _while_held(event: ButtonEvent | RotaryEvent) -> bool:
    """Return whether an event only matches while its button is held."""
    return isinstance(event, ButtonEvent) and event.while_held


def validate_event_matches(
    entities: Iterable[EntityMetadata],
    device_automation_triggers: Mapping[tuple[str, str], Any],
) -> None:
    """Validate that one `zha_event` fires at most one event of a quirk.

    An entity fires its first match for a `zha_event`, a button event entity trying
    the matches while held first, so a match an earlier one covers never fires.
    Each entity fires its own match, so the matches of two entities must not
    overlap, or one press or turn would fire both, as for a dial's push button and
    its rotation. Only matches while held may overlap across entities: they fire
    for the held button only.
    """
    matches: list[tuple[str, ButtonEvent | RotaryEvent, Mapping[str, Any]]] = []

    for entity_metadata in entities:
        if not isinstance(entity_metadata, EventEntityMetadata):
            continue

        # Entities on different endpoints may share a suffix
        suffix = (
            f"{entity_metadata.unique_id_suffix!r}"
            f" (endpoint {entity_metadata.endpoint_id})"
        )
        entity_matches = []
        for event in entity_metadata.events:
            if event.trigger is None:
                assert event.event_data is not None
                entity_matches.append((suffix, event, event.event_data))
            elif event.trigger in device_automation_triggers:
                entity_matches.append(
                    (suffix, event, device_automation_triggers[event.trigger])
                )

        # ZHA tries the matches while held first, keeping the order otherwise
        entity_matches.sort(key=lambda match: not _while_held(match[1]))
        for index, (_, earlier, earlier_data) in enumerate(entity_matches):
            for _, later, later_data in entity_matches[index + 1 :]:
                if _event_data_covers(earlier_data, later_data) and (
                    _while_held(later) or not _while_held(earlier)
                ):
                    raise ValueError(
                        f"Event {later} of {suffix} never fires: {earlier}"
                        " matches every zha_event it matches"
                    )

        matches.extend(entity_matches)

    for index, (suffix, event, data) in enumerate(matches):
        for other_suffix, other, other_data in matches[index + 1 :]:
            if (
                other_suffix != suffix
                and not (_while_held(event) and _while_held(other))
                and _event_data_overlap(data, other_data)
            ):
                raise ValueError(
                    f"Events {event} of {suffix} and {other} of"
                    f" {other_suffix} can match the same zha_event, which would"
                    " fire both"
                )


def validate_event_entities(entities: Iterable[EntityMetadata]) -> None:
    """Validate that a quirk's event entities, of any kind, have unique IDs."""
    seen: set[tuple[int, str]] = set()

    for entity_metadata in entities:
        if not isinstance(entity_metadata, EventEntityMetadata):
            continue

        key = (entity_metadata.endpoint_id, entity_metadata.unique_id_suffix)
        if key in seen:
            raise ValueError(
                f"Event entity {key[1]!r} on endpoint {key[0]} is defined twice"
            )
        seen.add(key)


# The names from before rotary event entities, which these cover as well
validate_button_event_entities = validate_event_entities
validate_button_event_matches = validate_event_matches
validate_button_event_triggers = validate_event_triggers


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
class EntityFilter:
    """Match entities. Every field that is set must match."""

    entity_cls: type[PlatformEntity] | None = attrs.field(default=None)
    platform: EntityPlatform | None = attrs.field(default=None)
    endpoint_id: int | None = attrs.field(default=None)
    cluster_id: int | None = attrs.field(default=None)
    cluster_type: ClusterType | None = attrs.field(default=None)
    unique_id_suffix: str | None = attrs.field(default=None)
    translation_key: str | None = attrs.field(default=None)
    device_class: str | None = attrs.field(default=None)
    function: Callable[[PlatformEntity], bool] | None = attrs.field(default=None)

    def __attrs_post_init__(self) -> None:
        """Validate the filter."""
        if self.cluster_type is not None and self.cluster_id is None:
            raise ValueError("`cluster_type` requires a `cluster_id`")

    def matches(self, entity: PlatformEntity) -> bool:
        """Return whether the entity matches the filter."""
        if self.entity_cls is not None and type(entity) is not self.entity_cls:
            return False
        if self.platform is not None and self.platform != entity.PLATFORM:
            return False
        if self.endpoint_id is not None or self.cluster_id is not None:
            # Only ZCL entities are bound to an endpoint and a cluster
            if not isinstance(entity, ZclPlatformEntity):
                return False
            if self.endpoint_id is not None and entity.endpoint.id != self.endpoint_id:
                return False
            if self.cluster_id is not None and not entity.targets_cluster(
                self.cluster_id, cluster_type=self.cluster_type
            ):
                return False
        if self.unique_id_suffix is not None and not entity.unique_id.endswith(
            "-" + self.unique_id_suffix.removeprefix("-")
        ):
            return False
        if (
            self.translation_key is not None
            and entity.translation_key != self.translation_key
        ):
            return False
        if self.device_class is not None and entity.device_class != self.device_class:
            return False
        if self.function is not None and not self.function(entity):
            return False
        return True


@attrs.define(frozen=True, kw_only=True, repr=True)
class AddedEntityMetadata:
    """Metadata to add an entity of a given class."""

    entity_cls: type[PlatformEntity] = attrs.field()
    endpoint_id: int | None = attrs.field()
    cluster_id: int | None = attrs.field()
    cluster_type: ClusterType = attrs.field()
    kwargs: frozendict[str, Any] = attrs.field(factory=frozendict, converter=frozendict)


@attrs.define(frozen=True, kw_only=True, repr=True)
class ReplacedEntityMetadata:
    """Metadata to replace the default entity of exactly `base_cls` matching a filter."""

    base_cls: type[PlatformEntity] = attrs.field()
    filter: EntityFilter = attrs.field()
    entity_cls: type[PlatformEntity] = attrs.field()
    kwargs: frozendict[str, Any] = attrs.field(factory=frozendict, converter=frozendict)


@attrs.define(frozen=True, kw_only=True, repr=True)
class ChangedEntityMetadata:
    """Metadata to change entity metadata for matching entities."""

    filter: EntityFilter = attrs.field()
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
    # `None` moves the entity to the main device, so `UNDEFINED` means no change
    new_child_device_id: str | None | UndefinedType = attrs.field(
        default=UNDEFINED,
        validator=attrs.validators.instance_of((str, type(None), UndefinedType)),
    )


@attrs.define(frozen=True, kw_only=True, repr=True)
class ChildDeviceMetadata:
    """Metadata for a child device: a logical part of the device, e.g. a gang."""

    id: str = attrs.field(
        validator=[attrs.validators.instance_of(str), attrs.validators.min_len(1)]
    )
    endpoint_ids: frozenset[int] = attrs.field(factory=frozenset, converter=frozenset)
    translation_key: str | None = attrs.field(default=None)
    translation_placeholders: frozendict[str, str] = attrs.field(
        factory=frozendict, converter=frozendict
    )
    fallback_name: str = attrs.field(validator=attrs.validators.instance_of(str))


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
    disabled_default_entities: tuple[EntityFilter, ...] = attrs.field(factory=tuple)
    changed_entity_metadata: tuple[ChangedEntityMetadata, ...] = attrs.field(
        factory=tuple
    )
    entity_metadata: tuple[EntityMetadata, ...] = attrs.field(factory=tuple)
    added_entities: tuple[AddedEntityMetadata, ...] = attrs.field(factory=tuple)
    replaced_entities: tuple[ReplacedEntityMetadata, ...] = attrs.field(factory=tuple)
    device_automation_triggers: frozendict[tuple[str, str], frozendict[str, str]] = (
        attrs.field(factory=frozendict, converter=recursive_freeze)
    )
    skip_configuration: bool = attrs.field(default=False)
    # `None` leaves child devices to ZHA, an empty tuple disables them
    child_devices: tuple[ChildDeviceMetadata, ...] | None = attrs.field(default=None)
