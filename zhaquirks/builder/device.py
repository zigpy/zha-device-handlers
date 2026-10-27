"""The ZHA device used by declarative (QuirkBuilder) quirks."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING, Any

# `discovery` must be imported before `zha.zigbee.device`: the platform modules
# it loads participate in an import cycle with the device module and cannot be
# loaded while `zha.zigbee.device` is only partially initialized.
from zha.application import Platform, discovery  # noqa: F401
from zha.application.platforms import BaseEntity, PlatformEntity
from zha.zigbee.device import Device
import zigpy.device
import zigpy.zcl

from zhaquirks.builder.discovery import discover_quirks_v2_entities
from zhaquirks.builder.metadata import QuirkDefinition

if TYPE_CHECKING:
    from zha.application.gateway import Gateway


class QuirkV2Device(Device):
    """Base ZHA device for QuirkBuilder."""

    def __init__(
        self,
        zigpy_device: zigpy.device.Device,
        gateway: Gateway,
        *,
        quirk_definition: QuirkDefinition,
    ) -> None:
        """Initialize the quirk device."""
        self._quirk_definition = quirk_definition
        super().__init__(zigpy_device, gateway)

    @property
    def quirk_metadata(self) -> QuirkDefinition:
        """Return the ZHA-level quirk metadata for this device."""
        return self._quirk_definition

    def discover_entities(self) -> Iterator[BaseEntity]:
        """Yield the default entities plus the quirk's exposed v2 entities."""
        yield from super().discover_entities()
        yield from discover_quirks_v2_entities(self)

    def _quirk_exposes_features(self) -> set[str]:
        return {f.feature for f in self._quirk_definition.exposes_features}

    def _resolve_manufacturer(self) -> str:
        if self._quirk_definition.friendly_name is not None:
            return self._quirk_definition.friendly_name.manufacturer
        return super()._resolve_manufacturer()

    def _resolve_model(self) -> str:
        if self._quirk_definition.friendly_name is not None:
            return self._quirk_definition.friendly_name.model
        return super()._resolve_model()

    @cached_property
    def device_alerts(self) -> Iterable[Any]:
        """Return device alerts for this device."""
        return self._quirk_definition.device_alerts

    def _quirk_skip_configuration(self) -> bool:
        return self._quirk_definition.skip_configuration

    def _quirk_device_automation_triggers(
        self,
    ) -> dict[tuple[str, str], dict[str, str]]:
        return dict(self._quirk_definition.device_automation_triggers)

    def _is_entity_removed_by_quirk(self, entity: PlatformEntity) -> bool:
        if entity.PLATFORM == Platform.VIRTUAL:
            return False

        for meta in self._quirk_definition.disabled_default_entities:
            if meta.unique_id_suffix is not None and not entity.unique_id.endswith(
                meta.unique_id_suffix
            ):
                continue
            if meta.endpoint_id is not None and entity.endpoint.id != meta.endpoint_id:
                continue
            if meta.cluster_id is not None and not entity.targets_cluster(
                meta.cluster_id
            ):
                continue
            if meta.function is not None and not meta.function(entity):
                continue
            return True

        return False

    def _apply_entity_metadata_changes(self, entity: PlatformEntity) -> None:
        if entity.PLATFORM == Platform.VIRTUAL:
            return

        for meta in self._quirk_definition.changed_entity_metadata:
            if meta.unique_id_suffix is not None and not entity.unique_id.endswith(
                meta.unique_id_suffix
            ):
                continue
            if meta.endpoint_id is not None and entity.endpoint.id != meta.endpoint_id:
                continue
            if meta.cluster_id is not None and not entity.targets_cluster(
                meta.cluster_id, cluster_type=meta.cluster_type
            ):
                continue
            if meta.function is not None and not meta.function(entity):
                continue

            if meta.new_primary is not None:
                entity._attr_primary = meta.new_primary
            if meta.new_unique_id is not None:
                entity._unique_id = meta.new_unique_id
            if meta.new_translation_key is not None:
                entity._attr_translation_key = meta.new_translation_key
            if meta.new_translation_placeholders is not None:
                entity._attr_translation_placeholders = (
                    meta.new_translation_placeholders
                )
            if meta.new_device_class is not None:
                entity._attr_device_class = meta.new_device_class
            if meta.new_state_class is not None:
                entity._attr_state_class = meta.new_state_class
            if meta.new_entity_category is not None:
                entity._attr_entity_category = meta.new_entity_category
            if meta.new_entity_registry_enabled_default is not None:
                entity._attr_entity_registry_enabled_default = (
                    meta.new_entity_registry_enabled_default
                )
            if meta.new_fallback_name is not None:
                entity._attr_fallback_name = meta.new_fallback_name


@dataclass(frozen=True)
class QuirkV2Factory:
    """Registry-entry factory that builds a `QuirkV2Device` bound to its definition."""

    base: type[QuirkV2Device]
    quirk_definition: QuirkDefinition

    def __call__(
        self, zigpy_device: zigpy.device.Device, gateway: Gateway
    ) -> QuirkV2Device:
        """Build the bound `QuirkV2Device` for a resolved zigpy device."""
        return self.base(zigpy_device, gateway, quirk_definition=self.quirk_definition)
