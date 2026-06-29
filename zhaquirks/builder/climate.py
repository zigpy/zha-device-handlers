"""Quirk-defined climate (thermostat) preset augmentation.

ZCL has no concept of the manufacturer-specific operating modes that TRVs expose
(away / eco / boost / schedule / holiday / frost protection / …), so ZHA used to
carry a hardcoded ``Thermostat`` subclass per manufacturer. This module lets a
quirk declare those presets instead, generating a ``Thermostat`` subclass and
registering it into ZHA's entity registry scoped to the quirk's devices.

The generated class is registered at a higher ``feature_priority`` than both the
generic ZHA ``Thermostat`` (1) and any remaining hardcoded manufacturer class (2),
so ZHA's discovery selects it and discards the others - there is no duplicate
climate entity. Because the generated class inherits ``Thermostat.__init__`` it
produces the same ``unique_id`` as the entity it replaces, so existing Home
Assistant installations keep their climate entity.

``register_thermostat_presets`` can be called directly from any quirk module
(v1 ``CustomDevice`` or v2 ``QuirkBuilder``); ``QuirkBuilder.thermostat_presets``
is a thin wrapper that derives the device scope from the builder.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING, Any

from zha.application.helpers import write_attributes_safe
from zha.application.platforms import (
    ClusterMatch,
    PlatformFeatureGroup,
    register_entity,
)
from zha.application.platforms.climate import Thermostat
from zha.application.platforms.climate.const import (
    ClimateEntityFeature,
    HVACMode,
    Preset,
)
from zigpy.zcl import (
    AttributeReadEvent,
    AttributeReportedEvent,
    AttributeUpdatedEvent,
    AttributeWrittenEvent,
)
from zigpy.zcl.clusters.hvac import Thermostat as ThermostatCluster

if TYPE_CHECKING:
    from zha.zigbee.device import Device
    from zha.zigbee.endpoint import Endpoint

_LOGGER = logging.getLogger(__name__)

# Priority above the generic Thermostat (1) and ZHA's hardcoded manufacturer
# classes (2), so a quirk-defined thermostat replaces them in ZHA discovery.
QUIRK_THERMOSTAT_FEATURE_PRIORITY = 3


class QuirksThermostat(Thermostat):
    """A ``Thermostat`` whose presets and HVAC modes come from quirk metadata.

    Generated subclasses set the class-level config below; this base implements
    the generic behavior. Mirrors the pattern ZHA's hardcoded manufacturer
    thermostats used (``recompute_capabilities`` / ``handle_attribute_updated`` /
    ``async_preset_handler``), driven by data instead of bespoke code.
    """

    # Attribute backing the active preset.
    _preset_attribute_name: str | None = None
    # Preset name -> value written to select it.
    _preset_write_values: dict[str, int] = {}
    # Value reported by the device -> preset name (may be many-to-one).
    _preset_read_values: dict[int, str] = {}
    # Value written to clear the active preset (when switching presets off).
    _preset_none_value: int | None = None
    # Optional fixed HVAC mode list (e.g. heat-only valves that can't turn off).
    _quirk_hvac_modes: list[HVACMode] | None = None
    # Cluster holding the preset attribute. None means the thermostat cluster
    # itself; set it (e.g. a Tuya MCU cluster) when the preset lives elsewhere.
    _preset_cluster_id: int | None = None

    def __init__(self, endpoint: Endpoint, device: Device, **kwargs) -> None:
        """Resolve the cluster the preset attribute lives on."""
        super().__init__(endpoint=endpoint, device=device, **kwargs)
        if self._preset_cluster_id is None:
            self._preset_cluster = self._cluster
        else:
            self._preset_cluster = endpoint.zigpy_endpoint.in_clusters[
                self._preset_cluster_id
            ]

    def on_add(self) -> None:
        """Listen for preset updates on a separate cluster, if configured."""
        super().on_add()
        if self._preset_cluster is self._cluster:
            return
        for event_type in (
            AttributeReadEvent,
            AttributeReportedEvent,
            AttributeUpdatedEvent,
            AttributeWrittenEvent,
        ):
            self._on_remove_callbacks.append(
                self._preset_cluster.on_event(
                    event_type.event_type, self._handle_preset_attribute_updated
                )
            )

    def _handle_preset_attribute_updated(
        self,
        event: AttributeReadEvent
        | AttributeReportedEvent
        | AttributeUpdatedEvent
        | AttributeWrittenEvent,
    ) -> None:
        """Update the active preset from an event on the preset cluster."""
        if (
            event.attribute_name == self._preset_attribute_name
            and event.value in self._preset_read_values
        ):
            self._preset = self._preset_read_values[event.value]
            self.maybe_emit_state_changed_event()

    def recompute_capabilities(self) -> None:
        """Recompute capabilities and feature flags."""
        super().recompute_capabilities()
        if self._preset_write_values:
            self._presets = list(self._preset_write_values)
            self._supported_features |= ClimateEntityFeature.PRESET_MODE

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return the list of available HVAC operation modes."""
        if self._quirk_hvac_modes is not None:
            return self._quirk_hvac_modes
        return super().hvac_modes

    def handle_attribute_updated(
        self,
        event: AttributeReadEvent
        | AttributeReportedEvent
        | AttributeUpdatedEvent
        | AttributeWrittenEvent,
    ) -> None:
        """Handle attribute update from device."""
        if (
            self._preset_attribute_name is not None
            and event.attribute_name == self._preset_attribute_name
            and event.value in self._preset_read_values
        ):
            self._preset = self._preset_read_values[event.value]
        super().handle_attribute_updated(event)

    async def async_preset_handler(self, preset: str, enable: bool = False) -> None:
        """Set the preset mode by writing the backing attribute."""
        value = self._preset_write_values[preset] if enable else self._preset_none_value
        if value is None:
            return
        await write_attributes_safe(
            self._preset_cluster,
            {self._preset_attribute_name: value},
            manufacturer=self._device.manufacturer_code,
        )


def register_thermostat_presets(
    *,
    manufacturers: frozenset[str] | set[str] | tuple[str, ...] | None = None,
    models: frozenset[str] | set[str] | tuple[str, ...] | None = None,
    attribute_name: str | None = None,
    presets: dict[str, int] | None = None,
    read_value_overrides: dict[int, str] | None = None,
    none_value: int | None = None,
    hvac_modes: list[HVACMode] | None = None,
    preset_cluster_id: int | None = None,
    required_clusters: tuple[int, ...] = (ThermostatCluster.cluster_id,),
    feature_priority: int = QUIRK_THERMOSTAT_FEATURE_PRIORITY,
    name: str | None = None,
) -> type[QuirksThermostat]:
    """Generate and register a quirk-defined thermostat entity.

    ``presets`` maps each preset name (a ``Preset`` member or custom string) to
    the value written to select it. The value written to clear a preset defaults
    to ``presets[Preset.NONE]`` and can be overridden with ``none_value``.
    ``read_value_overrides`` adds extra device-reported values that map to an
    already-defined preset (e.g. a TRV reporting two values for one holiday mode).
    ``hvac_modes`` fixes the HVAC mode list (e.g. ``[HVACMode.HEAT]`` for valves
    that cannot be turned off). ``preset_cluster_id`` is the cluster the preset
    attribute lives on when it isn't the thermostat cluster itself (e.g. a Tuya
    MCU cluster); it is added to the required clusters for discovery.

    The class is scoped to ``manufacturers`` and/or ``models`` so it only applies
    to the intended devices. At least one of them must be given.
    """
    if not manufacturers and not models:
        raise ValueError(
            "register_thermostat_presets requires manufacturers and/or models"
        )

    presets = dict(presets or {})
    if presets and attribute_name is None:
        raise ValueError("attribute_name is required when presets are defined")

    if none_value is None:
        none_value = presets.get(Preset.NONE)

    read_values: dict[int, str] = {value: name for name, value in presets.items()}
    read_values.update(read_value_overrides or {})

    server_clusters = set(required_clusters)
    if preset_cluster_id is not None:
        server_clusters.add(preset_cluster_id)

    cluster_match = ClusterMatch(
        server_clusters=frozenset(server_clusters),
        manufacturers=frozenset(manufacturers) if manufacturers else None,
        models=frozenset(models) if models else None,
        feature_priority=(PlatformFeatureGroup.THERMOSTAT_FAN, feature_priority),
        # A manufacturer preset cluster (e.g. a Tuya MCU cluster) has a renamed
        # ep_attribute, which discovery skips by default; opt in so the match
        # still sees it.
        match_renamed_clusters=preset_cluster_id is not None,
    )

    scope = "-".join(sorted(manufacturers or models or ()))
    namespace: dict[str, Any] = {
        "__doc__": f"Quirk-defined thermostat for {scope}.",
        "_preset_attribute_name": attribute_name,
        "_preset_write_values": presets,
        "_preset_read_values": read_values,
        "_preset_none_value": none_value,
        "_quirk_hvac_modes": hvac_modes,
        "_preset_cluster_id": preset_cluster_id,
        "_cluster_match": cluster_match,
    }
    generated = type(
        name or f"QuirksThermostat_{scope}", (QuirksThermostat,), namespace
    )

    register_entity(ThermostatCluster.cluster_id)(generated)
    _LOGGER.debug(
        "Registered quirk thermostat for %s with presets %s",
        scope,
        list(presets),
    )
    return generated


@dataclass(frozen=True)
class ThermostatPresetConfig:
    """A deferred ``QuirkBuilder.thermostat_presets()`` registration.

    Mirrors the keyword arguments of ``register_thermostat_presets``. The builder
    derives the device scope (manufacturers/models) at ``add_to_registry`` time
    and calls ``register()``.
    """

    attribute_name: str | None = None
    presets: dict[str, int] | None = None
    read_value_overrides: dict[int, str] | None = None
    none_value: int | None = None
    hvac_modes: list[HVACMode] | None = None
    preset_cluster_id: int | None = None
    required_clusters: tuple[int, ...] | None = None
    name: str | None = None

    def register(
        self,
        manufacturers: frozenset[str] | set[str] | tuple[str, ...] | None,
        models: frozenset[str] | set[str] | tuple[str, ...] | None,
    ) -> type[QuirksThermostat]:
        """Register the quirk thermostat scoped to the given manufacturers/models."""
        # Only forward required_clusters when set, so the helper's default applies.
        extra = (
            {}
            if self.required_clusters is None
            else {"required_clusters": self.required_clusters}
        )
        return register_thermostat_presets(
            manufacturers=manufacturers,
            models=models,
            attribute_name=self.attribute_name,
            presets=self.presets,
            read_value_overrides=self.read_value_overrides,
            none_value=self.none_value,
            hvac_modes=self.hvac_modes,
            preset_cluster_id=self.preset_cluster_id,
            name=self.name,
            **extra,
        )
