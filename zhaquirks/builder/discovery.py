"""Construction of ZHA entities from quirks v2 metadata.

`discover_quirks_v2_entities` turns the declarative `EntityMetadata` carried by a
`QuirkDefinition` into ZHA platform entities, instantiating ZHA's base entity
classes with plain keyword arguments. This used to live in ZHA's discovery
module reading a zigpy `CustomZigpyDevice`; it now lives in the quirks layer and is
driven by `QuirkV2Device`.
"""

from __future__ import annotations

from collections.abc import Iterator
import logging
from typing import TYPE_CHECKING, Any

from zha.application import Platform
from zha.application.platforms import (
    AttrConfig,
    ClusterConfig,
    PlatformEntity,
    binary_sensor,
    button,
    number,
    select,
    sensor,
    switch,
)
from zha.application.platforms.virtual import VirtualEntity
from zigpy.zcl import ClusterType, ReportingConfig

from zhaquirks.builder.metadata import (
    BinarySensorMetadata,
    ClusterConfigMetadata,
    EntityMetadata,
    NumberMetadata,
    SwitchMetadata,
    WriteAttributeButtonMetadata,
    ZCLCommandButtonMetadata,
    ZCLEnumMetadata,
    ZCLSensorMetadata,
)

if TYPE_CHECKING:
    from zha.zigbee.device import Device

_LOGGER = logging.getLogger(__name__)

QUIRKS_ENTITY_META_TO_ENTITY_CLASS: dict[
    tuple[Platform, type], type[PlatformEntity]
] = {
    (Platform.BUTTON, WriteAttributeButtonMetadata): button.WriteAttributeButton,
    (Platform.BUTTON, ZCLCommandButtonMetadata): button.Button,
    (Platform.BINARY_SENSOR, BinarySensorMetadata): binary_sensor.BinarySensor,
    (Platform.SENSOR, ZCLEnumMetadata): sensor.EnumSensor,
    (Platform.SENSOR, ZCLSensorMetadata): sensor.Sensor,
    (Platform.SELECT, ZCLEnumMetadata): select.ZCLEnumSelectEntity,
    (Platform.NUMBER, NumberMetadata): number.NumberConfigurationEntity,
    (Platform.SWITCH, SwitchMetadata): switch.ConfigurableAttributeSwitch,
}


def _generic_kwargs(entity_metadata: EntityMetadata) -> dict[str, Any]:
    """Return the keyword arguments common to every quirk entity."""
    return {
        "from_quirk": True,
        "fallback_name": entity_metadata.fallback_name,
        "translation_key": entity_metadata.translation_key,
        "translation_placeholders": entity_metadata.translation_placeholders or None,
        "unique_id_suffix": entity_metadata.resolved_unique_id_suffix,
        "entity_type": entity_metadata.entity_type,
        "primary": entity_metadata.primary,
        "initially_disabled": entity_metadata.initially_disabled,
    }


def _platform_kwargs(entity_metadata: EntityMetadata) -> dict[str, Any]:
    """Return the platform-specific keyword arguments for a quirk entity."""
    if isinstance(entity_metadata, ZCLSensorMetadata):
        return {
            "attribute_name": entity_metadata.attribute_name,
            "attribute_converter": entity_metadata.attribute_converter,
            "divisor": entity_metadata.divisor,
            "multiplier": entity_metadata.multiplier,
            "device_class": entity_metadata.device_class,
            "state_class": entity_metadata.state_class,
            "unit": entity_metadata.unit,
        }
    if isinstance(entity_metadata, NumberMetadata):
        return {
            "attribute_name": entity_metadata.attribute_name,
            "min_value": entity_metadata.min,
            "max_value": entity_metadata.max,
            "step": entity_metadata.step,
            "multiplier": entity_metadata.multiplier,
            "device_class": entity_metadata.device_class,
            "unit": entity_metadata.unit,
            "mode": entity_metadata.mode,
        }
    if isinstance(entity_metadata, SwitchMetadata):
        return {
            "attribute_name": entity_metadata.attribute_name,
            "invert_attribute_name": entity_metadata.invert_attribute_name,
            "force_inverted": entity_metadata.force_inverted,
            "off_value": entity_metadata.off_value,
            "on_value": entity_metadata.on_value,
        }
    if isinstance(entity_metadata, BinarySensorMetadata):
        return {
            "attribute_name": entity_metadata.attribute_name,
            "attribute_converter": entity_metadata.attribute_converter,
            "device_class": entity_metadata.device_class,
        }
    if isinstance(entity_metadata, ZCLEnumMetadata):
        return {
            "attribute_name": entity_metadata.attribute_name,
            "enum": entity_metadata.enum,
        }
    if isinstance(entity_metadata, WriteAttributeButtonMetadata):
        return {
            "attribute_name": entity_metadata.attribute_name,
            "attribute_value": entity_metadata.attribute_value,
        }
    if isinstance(entity_metadata, ZCLCommandButtonMetadata):
        return {
            "command_name": entity_metadata.command_name,
            "command_args": entity_metadata.args,
            "command_kwargs": entity_metadata.kwargs,
        }
    return {}


class QuirkClusterConfigEntity(VirtualEntity):
    """Entity-less carrier for quirk-declared cluster bind/write/reporting config."""


def _discover_cluster_config_entities(
    device: Device, cluster_configs: tuple[ClusterConfigMetadata, ...]
) -> Iterator[PlatformEntity]:
    """Yield config-only virtual entities for entity-less cluster configs."""
    for cluster_config in cluster_configs:
        endpoint_id = cluster_config.endpoint_id
        cluster_id = cluster_config.cluster_id
        cluster_type = cluster_config.cluster_type

        if endpoint_id not in device.endpoints:
            _LOGGER.warning(
                "Device: %s-%s does not have an endpoint with id: %s - unable to "
                "apply cluster config: %s",
                str(device.ieee),
                device.name,
                endpoint_id,
                cluster_config,
            )
            continue

        endpoint = device.endpoints[endpoint_id]
        cluster = (
            endpoint.zigpy_endpoint.in_clusters.get(cluster_id)
            if cluster_type is ClusterType.Server
            else endpoint.zigpy_endpoint.out_clusters.get(cluster_id)
        )

        if cluster is None:
            _LOGGER.warning(
                "Device: %s-%s does not have a cluster with id: %s - "
                "unable to apply cluster config: %s",
                str(device.ieee),
                device.name,
                cluster_id,
                cluster_config,
            )
            continue

        # Attribute names stay strings - quirks can reference manufacturer
        # specific attributes outside the cluster's schema; the aggregation and
        # configure flow handle both names and ZCLAttributeDef objects.
        attributes = {
            attr.attribute_name: AttrConfig(
                read_on_startup=attr.read_on_startup,
                reporting=(
                    ReportingConfig(
                        min_interval=attr.reporting_config.min_interval,
                        max_interval=attr.reporting_config.max_interval,
                        reportable_change=attr.reporting_config.reportable_change,
                    )
                    if attr.reporting_config is not None
                    else None
                ),
            )
            for attr in cluster_config.attributes
        }
        config = {
            cluster.cluster_id: ClusterConfig(
                bind=cluster_config.bind,
                attributes=attributes,
                attribute_writes=dict(cluster_config.attribute_writes),
            )
        }

        # One config record per (endpoint, cluster, type); the suffix only needs
        # to disambiguate a server and client config on the same cluster.
        suffix = f"cluster_config-{cluster_id:#06x}-{cluster_type.name.lower()}"

        entity = QuirkClusterConfigEntity(
            endpoint=endpoint,
            device=device,
            cluster=cluster,
            from_quirk=True,
            unique_id_suffix=suffix,
        )
        if cluster_type is ClusterType.Server:
            entity._server_cluster_config = config
        else:
            entity._client_cluster_config = config

        yield entity


def discover_quirks_v2_entities(device: Device) -> Iterator[PlatformEntity]:
    """Discover entities exposed by a device's quirks v2 metadata."""
    quirk_metadata = device.quirk_metadata
    if quirk_metadata is None or (
        not quirk_metadata.entity_metadata and not quirk_metadata.cluster_configs
    ):
        _LOGGER.debug(
            "Device: %s-%s does not expose any quirks v2 entities",
            str(device.ieee),
            device.name,
        )
        return

    yield from _discover_cluster_config_entities(device, quirk_metadata.cluster_configs)

    for entity_metadata in quirk_metadata.entity_metadata:
        endpoint_id = entity_metadata.endpoint_id
        cluster_id = entity_metadata.cluster_id
        cluster_type = entity_metadata.cluster_type

        if endpoint_id not in device.endpoints:
            _LOGGER.warning(
                "Device: %s-%s does not have an endpoint with id: %s - unable to "
                "create entity with metadata: %s",
                str(device.ieee),
                device.name,
                endpoint_id,
                entity_metadata,
            )
            continue

        endpoint = device.endpoints[endpoint_id]
        cluster = (
            endpoint.zigpy_endpoint.in_clusters.get(cluster_id)
            if cluster_type is ClusterType.Server
            else endpoint.zigpy_endpoint.out_clusters.get(cluster_id)
        )

        if cluster is None:
            _LOGGER.warning(
                "Device: %s-%s does not have a cluster with id: %s - "
                "unable to create entity with metadata: %s",
                str(device.ieee),
                device.name,
                cluster_id,
                entity_metadata,
            )
            continue

        platform = Platform(entity_metadata.entity_platform.value)
        entity_class = QUIRKS_ENTITY_META_TO_ENTITY_CLASS.get(
            (platform, type(entity_metadata))
        )

        if entity_class is None:
            _LOGGER.warning(
                "Device: %s-%s has an entity with metadata: %s that does not have an "
                "entity class mapping - unable to create entity",
                str(device.ieee),
                device.name,
                entity_metadata,
            )
            continue

        entity = entity_class(
            endpoint=endpoint,
            device=device,
            cluster=cluster,
            **_generic_kwargs(entity_metadata),
            **_platform_kwargs(entity_metadata),
        )

        # Translate quirks v2 reporting/attribute-init metadata into a
        # per-instance cluster config that the cluster_config aggregator picks up
        # alongside the entity's normal (class-level) declarations.
        attr_name = getattr(entity_metadata, "attribute_name", None)
        if attr_name:
            reporting_config = getattr(entity_metadata, "reporting_config", None)
            if reporting_config is not None:
                attr_config = AttrConfig(
                    read_on_startup=False,
                    reporting=ReportingConfig(
                        min_interval=reporting_config.min_interval,
                        max_interval=reporting_config.max_interval,
                        reportable_change=reporting_config.reportable_change,
                    ),
                )
                bind = True
            else:
                attr_config = AttrConfig(
                    read_on_startup=(
                        not entity_metadata.attribute_initialized_from_cache
                    ),
                )
                bind = False

            # Keep attr_name as a string here - quirks v2 entities can reference
            # attribute names that aren't part of the cluster's attribute schema
            # (e.g. manufacturer-specific extensions); aggregation/configure handle
            # both name and ZCLAttributeDef.
            config = {
                cluster.cluster_id: ClusterConfig(
                    bind=bind,
                    attributes={attr_name: attr_config},
                ),
            }

            if cluster_type is ClusterType.Server:
                entity._server_cluster_config = config
            else:
                entity._client_cluster_config = config

        yield entity

        _LOGGER.debug(
            "'%s' platform -> '%s' using cluster 0x%04x",
            platform,
            entity_class.__name__,
            cluster.cluster_id,
        )
