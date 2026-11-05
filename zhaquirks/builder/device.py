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
from zha.application.platforms import PlatformEntity, ZclPlatformEntity
from zha.zigbee.device import BaseDevice, ZigbeeDevice
import zigpy.device
import zigpy.zcl
from zigpy.zcl import ClusterType

from zhaquirks.builder.discovery import (
    discover_quirks_v2_entities,
    quirk_unique_id_base,
)
from zhaquirks.builder.metadata import AddedEntityMetadata, QuirkDefinition

if TYPE_CHECKING:
    from zha.application.gateway import Gateway


def create_added_entities(
    device: BaseDevice, added_entities: Iterable[AddedEntityMetadata]
) -> Iterator[PlatformEntity]:
    """Create the quirk's added entities for the device."""
    # An exception would end this generator, so one failing entity is skipped
    for added in added_entities:
        try:
            entity = _create_added_entity(device, added)
        except Exception:  # noqa: BLE001
            device.error("Failed to create added entity %r", added, exc_info=True)
            continue

        yield entity


def _create_added_entity(
    device: BaseDevice, added: AddedEntityMetadata
) -> PlatformEntity:
    if not issubclass(added.entity_cls, ZclPlatformEntity):
        return added.entity_cls(device, unique_id=str(device.ieee), **added.kwargs)

    # Only Zigbee devices have endpoints and clusters
    assert isinstance(device, ZigbeeDevice)

    endpoint = device.endpoints[added.endpoint_id]
    clusters = (
        endpoint.zigpy_endpoint.in_clusters
        if added.cluster_type is ClusterType.Server
        else endpoint.zigpy_endpoint.out_clusters
    )

    return added.entity_cls(
        endpoint=endpoint,
        device=device,
        cluster=clusters[added.cluster_id],
        unique_id=quirk_unique_id_base(device, endpoint),
        **added.kwargs,
    )


class QuirkV2Device(ZigbeeDevice):
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

    def discover_entities(self) -> Iterator[PlatformEntity]:
        """Yield the default entities plus the quirk's exposed and added entities."""
        entities: list[PlatformEntity] = []

        try:
            for entity in super().discover_entities():
                entities.append(entity)
        except Exception:
            # Keep the entities discovered before the failure, as ZHA does
            yield from self._replace_entities(entities)
            raise

        yield from self._replace_entities(entities)
        yield from discover_quirks_v2_entities(self)
        yield from create_added_entities(self, self._quirk_definition.added_entities)

    def _replace_entities(self, entities: list[PlatformEntity]) -> list[PlatformEntity]:
        """Replace the default entities matched by the quirk's replacements."""
        for replaced in self._quirk_definition.replaced_entities:
            indices = [
                index
                for index, entity in enumerate(entities)
                if type(entity) is replaced.base_cls and replaced.filter.matches(entity)
            ]

            # Discovery yields an entity twice for a cluster that is both an input and
            # an output cluster. ZHA keeps the first one, so it is the one replaced.
            matched = {(entities[i].PLATFORM, entities[i].unique_id) for i in indices}

            if len(matched) != 1:
                self.error(
                    "Replacement %r must match one entity, matched %d",
                    replaced,
                    len(matched),
                )
                continue

            index = indices[0]
            entity = entities[index]

            kwargs = dict(replaced.kwargs)

            if isinstance(entity, ZclPlatformEntity):
                kwargs["endpoint"] = entity.endpoint
                kwargs["cluster"] = entity.cluster

            try:
                new_entity = replaced.entity_cls(
                    device=self,
                    unique_id=entity.unique_id_base,
                    **kwargs,
                )
            except Exception:  # noqa: BLE001
                self.error("Failed to create replacement %r", replaced, exc_info=True)
                continue

            if new_entity.unique_id != entity.unique_id:
                self.error(
                    "Replacement %r changes the unique ID from %s to %s",
                    replaced,
                    entity.unique_id,
                    new_entity.unique_id,
                )
                continue

            entities[index] = new_entity

        return entities

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

        return any(
            entity_filter.matches(entity)
            for entity_filter in self._quirk_definition.disabled_default_entities
        )

    def _apply_entity_metadata_changes(self, entity: PlatformEntity) -> None:
        if entity.PLATFORM == Platform.VIRTUAL:
            return

        for meta in self._quirk_definition.changed_entity_metadata:
            if not meta.filter.matches(entity):
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
