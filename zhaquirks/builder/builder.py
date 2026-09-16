"""Quirks v2 builder."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
import inspect
import logging
import pathlib
from types import FrameType
from typing import Any, Self, overload

from frozendict import frozendict
from zha.application import (  # noqa: F401
    EntityPlatform,
    EntityType,
    # `discovery` must be imported before `zha.zigbee.device`: the platform
    # modules it loads participate in an import cycle with the device module and
    # cannot be loaded while `zha.zigbee.device` is only partially initialized.
    discovery,
)
from zha.application.platforms.binary_sensor.device_class import BinarySensorDeviceClass
from zha.application.platforms.number.device_class import NumberDeviceClass
from zha.application.platforms.sensor.device_class import (
    SensorDeviceClass,
    SensorStateClass,
)
from zha.quirks import (
    DEVICE_REGISTRY,
    DeviceMatch,
    DeviceRegistry,
    FilterType,
    ModelInfo,
    QuirkRegistryEntry,
    QuirkSource,
    ReplaceZigpyDevice,
)
from zha.zigbee.device import Device
import zigpy.device
import zigpy.profiles.zha
from zigpy.typing import UNDEFINED, UndefinedType
from zigpy.zcl import Cluster, ClusterType
from zigpy.zcl.foundation import ZCLAttributeDef
from zigpy.zdo.types import NodeDescriptor

from zhaquirks.builder.device import QuirkV2Device, QuirkV2Factory
from zhaquirks.builder.metadata import (
    BinarySensorMetadata,
    ChangedEntityMetadata,
    DeviceAlertLevel,
    DeviceAlertMetadata,
    EntityMetadata,
    ExposesFeatureMetadata,
    FriendlyNameMetadata,
    NumberMetadata,
    PreventDefaultEntityCreationMetadata,
    QuirkDefinition,
    ReportingConfig,
    SwitchMetadata,
    WriteAttributeButtonMetadata,
    ZCLCommandButtonMetadata,
    ZCLEnumMetadata,
    ZCLSensorMetadata,
)
from zhaquirks.device import BaseCustomDevice, CustomZigpyDevice

_LOGGER = logging.getLogger(__name__)

# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-arguments

type DeviceOp = Callable[[zigpy.device.Device], None]


@dataclass(frozen=True)
class AddCluster:
    """Add a cluster to an endpoint.

    `cluster` is either a bare cluster id or a `Cluster` subclass. When
    `constant_attributes` is provided (mapping `ZCLAttributeDef` to value), the
    values are served by the cluster without contacting the device; this
    requires `cluster` to be a `CustomCluster` subclass.
    """

    cluster: int | type[Cluster]
    endpoint_id: int = 1
    cluster_type: ClusterType = ClusterType.Server
    constant_attributes: frozendict[ZCLAttributeDef, Any] = field(
        default_factory=frozendict
    )

    def __call__(self, device: zigpy.device.Device) -> zigpy.device.Device:
        """Apply this operation to the given zigpy device."""
        if self.endpoint_id not in device.endpoints:
            _LOGGER.warning(
                "Cannot add cluster to missing endpoint %s on %s",
                self.endpoint_id,
                device,
            )
            return device
        endpoint = device.endpoints[self.endpoint_id]
        is_server = self.cluster_type == ClusterType.Server

        if isinstance(self.cluster, int):
            cluster = None
            cluster_id = self.cluster
        else:
            cluster = self.cluster(endpoint, is_server=is_server)
            cluster_id = cluster.cluster_id

        if is_server:
            cluster = endpoint.add_input_cluster(cluster_id, cluster)
        else:
            cluster = endpoint.add_output_cluster(cluster_id, cluster)

        if self.constant_attributes:
            cluster._CONSTANT_ATTRIBUTES = {
                attribute.id: value
                for attribute, value in self.constant_attributes.items()
            }

        return device


@dataclass(frozen=True)
class RemoveCluster:
    """Remove a cluster from an endpoint."""

    cluster_id: int
    endpoint_id: int = 1
    cluster_type: ClusterType = ClusterType.Server

    def __call__(self, device: zigpy.device.Device) -> zigpy.device.Device:
        """Apply this operation to the given zigpy device."""
        if self.endpoint_id not in device.endpoints:
            _LOGGER.warning(
                "Cannot remove cluster from missing endpoint %s on %s",
                self.endpoint_id,
                device,
            )
            return device
        endpoint = device.endpoints[self.endpoint_id]
        if self.cluster_type == ClusterType.Server:
            endpoint.in_clusters.pop(self.cluster_id, None)
        else:
            endpoint.out_clusters.pop(self.cluster_id, None)

        return device


@dataclass(frozen=True)
class ReplaceCluster:
    """Replace a cluster on an endpoint with a `Cluster` subclass.

    `cluster_id` identifies the cluster to remove and defaults to the
    replacement's own cluster id. Cached attribute values of the replaced
    cluster (e.g. restored from the database) carry over to the replacement.
    """

    cluster: type[Cluster]
    cluster_id: int | None = None
    endpoint_id: int = 1
    cluster_type: ClusterType = ClusterType.Server

    def __call__(self, device: zigpy.device.Device) -> zigpy.device.Device:
        """Apply this operation to the given zigpy device."""
        if self.endpoint_id not in device.endpoints:
            _LOGGER.warning(
                "Cannot replace cluster on missing endpoint %s on %s",
                self.endpoint_id,
                device,
            )
            return device
        endpoint = device.endpoints[self.endpoint_id]
        is_server = self.cluster_type == ClusterType.Server
        removed_cluster_id = (
            self.cluster.cluster_id if self.cluster_id is None else self.cluster_id
        )

        if is_server:
            old_cluster = endpoint.in_clusters.pop(removed_cluster_id, None)
        else:
            old_cluster = endpoint.out_clusters.pop(removed_cluster_id, None)

        new_cluster = self.cluster(endpoint, is_server=is_server)
        if is_server:
            endpoint.add_input_cluster(new_cluster.cluster_id, new_cluster)
        else:
            endpoint.add_output_cluster(new_cluster.cluster_id, new_cluster)

        if old_cluster is not None:
            new_cluster._attr_cache_internal = old_cluster._attr_cache.clone(
                new_cluster
            )

        return device


@dataclass(frozen=True)
class ReplaceClusterOccurrences:
    """Replace a cluster with a `Cluster` subclass on every endpoint."""

    cluster: type[Cluster]
    cluster_types: tuple[ClusterType, ...] = (ClusterType.Server, ClusterType.Client)

    def __call__(self, device: zigpy.device.Device) -> zigpy.device.Device:
        """Apply this operation to the given zigpy device."""
        for endpoint in device.non_zdo_endpoints:
            if (
                ClusterType.Server in self.cluster_types
                and self.cluster.cluster_id in endpoint.in_clusters
            ):
                device = ReplaceCluster(
                    cluster=self.cluster,
                    endpoint_id=endpoint.endpoint_id,
                    cluster_type=ClusterType.Server,
                )(device)

            if (
                ClusterType.Client in self.cluster_types
                and self.cluster.cluster_id in endpoint.out_clusters
            ):
                device = ReplaceCluster(
                    cluster=self.cluster,
                    endpoint_id=endpoint.endpoint_id,
                    cluster_type=ClusterType.Client,
                )(device)

        return device


@dataclass(frozen=True)
class AddEndpoint:
    """Add an endpoint to a device, if it does not already exist."""

    endpoint_id: int
    profile_id: int = zigpy.profiles.zha.PROFILE_ID
    device_type: int = 0xFF

    def __call__(self, device: zigpy.device.Device) -> zigpy.device.Device:
        """Apply this operation to the given zigpy device."""
        if self.endpoint_id in device.endpoints:
            return device
        endpoint = device.add_endpoint(self.endpoint_id)
        endpoint.profile_id = self.profile_id
        endpoint.device_type = self.device_type

        return device


@dataclass(frozen=True)
class RemoveEndpoint:
    """Remove an endpoint from a device."""

    endpoint_id: int

    def __call__(self, device: zigpy.device.Device) -> zigpy.device.Device:
        """Apply this operation to the given zigpy device."""
        device.endpoints.pop(self.endpoint_id, None)

        return device


@dataclass(frozen=True)
class ReplaceEndpoint:
    """Set the profile and device type of an endpoint, creating it if needed."""

    endpoint_id: int
    profile_id: int = zigpy.profiles.zha.PROFILE_ID
    device_type: int = 0xFF

    def __call__(self, device: zigpy.device.Device) -> zigpy.device.Device:
        """Apply this operation to the given zigpy device."""
        if self.endpoint_id in device.endpoints:
            endpoint = device.endpoints[self.endpoint_id]
        else:
            endpoint = device.add_endpoint(self.endpoint_id)
        endpoint.profile_id = self.profile_id
        endpoint.device_type = self.device_type

        return device


@dataclass(frozen=True)
class SetNodeDescriptor:
    """Replace the node descriptor of a device."""

    node_descriptor: NodeDescriptor

    def __call__(self, device: zigpy.device.Device) -> zigpy.device.Device:
        """Apply this operation to the given zigpy device."""
        device.node_desc = self.node_descriptor.freeze()

        return device


@dataclass(frozen=True)
class SetModelInfo:
    """Override the manufacturer and/or model of a device."""

    manufacturer: str | None = None
    model: str | None = None

    def __call__(self, device: zigpy.device.Device) -> zigpy.device.Device:
        """Apply this operation to the given zigpy device."""
        if self.manufacturer is not None:
            device.manufacturer = self.manufacturer
        if self.model is not None:
            device.model = self.model

        return device


@dataclass(frozen=True)
class SetDeviceAutomationTriggers:
    """Set the quirk-defined device automation triggers on a device."""

    triggers: frozendict[tuple[str, str], frozendict[str, str]]

    def __call__(self, device: zigpy.device.Device) -> zigpy.device.Device:
        """Apply this operation to the given zigpy device."""
        device.device_automation_triggers = dict(self.triggers)

        return device


class QuirkBuilder:
    """Builder compiling a declarative quirk into a registered `Device` subclass."""

    def __init__(
        self,
        manufacturer: str | None | UndefinedType = UNDEFINED,
        model: str | None | UndefinedType = UNDEFINED,
        registry: DeviceRegistry = DEVICE_REGISTRY,
    ) -> None:
        """Initialize the quirk builder."""
        self.registry: DeviceRegistry = registry
        self.manufacturer_model_metadata: list[ModelInfo] = []
        self.friendly_name_metadata: FriendlyNameMetadata | None = None
        self.exposes_features: list[ExposesFeatureMetadata] = []
        self.device_alerts: list[DeviceAlertMetadata] = []
        self.disabled_default_entities: list[PreventDefaultEntityCreationMetadata] = []
        self.changed_entity_metadata: list[ChangedEntityMetadata] = []
        self.filters: list[FilterType] = []
        self.firmware_version_min: int | None = None
        self.firmware_version_max: int | None = None
        self.firmware_version_allow_missing: bool = True
        self.custom_device_class: type[Device] | None = None
        self.custom_zigpy_device_class: type[BaseCustomDevice] = CustomZigpyDevice
        self.device_node_descriptor: NodeDescriptor | None = None
        self.skip_device_configuration: bool = False
        self.removes_endpoint_ops: list[RemoveEndpoint] = []
        self.adds_endpoint_ops: list[AddEndpoint] = []
        self.replaces_endpoint_ops: list[ReplaceEndpoint] = []
        self.removes_ops: list[RemoveCluster] = []
        self.adds_ops: list[AddCluster] = []
        self.replaces_ops: list[ReplaceCluster] = []
        self.replace_occurrences_ops: list[ReplaceClusterOccurrences] = []
        self.entity_metadata: list[EntityMetadata] = []
        self.device_automation_triggers_metadata: dict[
            tuple[str, str], dict[str, str]
        ] = {}

        current_frame: FrameType = inspect.currentframe()
        caller: FrameType = current_frame.f_back
        self.quirk_file = pathlib.Path(caller.f_code.co_filename)
        self.quirk_file_line = caller.f_lineno
        self.quirk_module: str = caller.f_globals["__name__"]

        if manufacturer is not UNDEFINED or model is not UNDEFINED:
            self.applies_to(
                manufacturer=manufacturer if manufacturer is not UNDEFINED else None,
                model=model if model is not UNDEFINED else None,
            )

    def _add_entity_metadata(self, entity_metadata: EntityMetadata) -> Self:
        """Register new entity metadata and validate config."""
        if entity_metadata.primary and any(
            entity.primary for entity in self.entity_metadata
        ):
            raise ValueError("Only one primary entity can be defined per device")

        self.entity_metadata.append(entity_metadata)
        return self

    @overload
    def applies_to(self, manufacturer: str, model: str) -> Self: ...

    @overload
    def applies_to(self, manufacturer: str, model: None) -> Self: ...

    @overload
    def applies_to(self, manufacturer: None, model: str) -> Self: ...

    def applies_to(self, manufacturer: str | None, model: str | None) -> Self:
        """Register this quirk for the specified manufacturer and model."""
        if manufacturer is None and model is None:
            raise ValueError(
                "A manufacturer and/or model must be specified for a v2 quirk."
            )

        self.manufacturer_model_metadata.append(ModelInfo(manufacturer, model))
        return self

    # backward compatibility
    also_applies_to = applies_to

    def filter(self, filter_function: FilterType) -> Self:
        """Add a filter and returns self.

        The filter function should take a single argument, a zigpy.device.Device
        instance, and return a boolean if the condition the filter is testing
        passes.

        Ex: def some_filter(device: zigpy.device.Device) -> bool:
        """
        self.filters.append(filter_function)
        return self

    def firmware_version_filter(
        self,
        min_version: int | None = None,
        max_version: int | None = None,
        allow_missing: bool = True,
    ) -> Self:
        """Add a firmware version filter and returns self.

        The min_version and max_version are integers representing the firmware version,
        minimum inclusive but maximum exclusive. If allow_missing is True, the filter
        will pass if the device does not have a firmware version.
        """
        self.firmware_version_min = min_version
        self.firmware_version_max = max_version
        self.firmware_version_allow_missing = allow_missing
        return self

    def device_class(
        self, custom_device_class: type[Device] | type[BaseCustomDevice]
    ) -> Self:
        """Use `zha_device_class` or `zigpy_device_class` instead (legacy compatibility)."""
        if issubclass(custom_device_class, Device):
            return self.zha_device_class(custom_device_class)
        else:
            return self.zigpy_device_class(custom_device_class)

    def zha_device_class(self, custom_device_class: type[Device]) -> Self:
        """Set the ZHA `Device` subclass used as the base of this quirk's class."""
        self.custom_device_class = custom_device_class
        return self

    def zigpy_device_class(self, custom_device_class: type[BaseCustomDevice]) -> Self:
        """Replace the zigpy device object with an instance of the given class."""
        if not issubclass(custom_device_class, BaseCustomDevice):
            raise TypeError(
                f"{custom_device_class!r} is not a subclass of BaseCustomDevice"
            )
        self.custom_zigpy_device_class = custom_device_class
        return self

    def node_descriptor(self, node_descriptor: NodeDescriptor) -> Self:
        """Set the node descriptor and returns self."""
        self.device_node_descriptor = node_descriptor.freeze()
        return self

    def skip_configuration(self, skip_configuration: bool = True) -> Self:
        """Set the skip_configuration and returns self.

        If skip_configuration is True, reporting configuration will not be
        applied to any cluster on this device.
        """
        self.skip_device_configuration = skip_configuration
        return self

    def adds(
        self,
        cluster: int | type[Cluster],
        cluster_type: ClusterType = ClusterType.Server,
        endpoint_id: int = 1,
        constant_attributes: dict[ZCLAttributeDef, Any] | None = None,
    ) -> Self:
        """Add an `AddCluster` operation and return self.

        This method allows adding a cluster to a device when the quirk is applied.

        If cluster is an int, it will be used as the cluster_id. If cluster is a
        subclass of Cluster or CustomCluster, it will be used to create a new
        cluster instance.

        If constant_attributes is provided, it should be a dictionary of ZCLAttributeDef
        instances and their values. These attributes will be added to the cluster when
        the quirk is applied and the values will be constant.
        """
        self.adds_ops.append(
            AddCluster(
                cluster=cluster,
                endpoint_id=endpoint_id,
                cluster_type=cluster_type,
                constant_attributes=frozendict(constant_attributes or {}),
            )
        )
        return self

    def removes(
        self,
        cluster_id: int,
        cluster_type: ClusterType = ClusterType.Server,
        endpoint_id: int = 1,
    ) -> Self:
        """Add a `RemoveCluster` operation and return self.

        This method allows removing a cluster from a device when the quirk is applied.
        """
        self.removes_ops.append(
            RemoveCluster(
                cluster_id=cluster_id,
                endpoint_id=endpoint_id,
                cluster_type=cluster_type,
            )
        )
        return self

    def replaces(
        self,
        replacement_cluster_class: type[Cluster],
        cluster_id: int | None = None,
        cluster_type: ClusterType = ClusterType.Server,
        endpoint_id: int = 1,
    ) -> Self:
        """Add a `ReplaceCluster` operation and return self.

        This method allows replacing a cluster on a device when the quirk is applied.

        replacement_cluster_class should be a subclass of Cluster or CustomCluster and
        will be used to create a new cluster instance to replace the existing cluster.

        If cluster_id is provided, it will be used as the cluster_id for the cluster to
        be removed. If cluster_id is not provided, the cluster_id of the replacement
        cluster will be used.
        """
        self.replaces_ops.append(
            ReplaceCluster(
                cluster=replacement_cluster_class,
                cluster_id=cluster_id,
                endpoint_id=endpoint_id,
                cluster_type=cluster_type,
            )
        )
        return self

    def replace_cluster_occurrences(
        self,
        replacement_cluster_class: type[Cluster],
        replace_server_instances: bool = True,
        replace_client_instances: bool = True,
    ) -> Self:
        """Add a `ReplaceClusterOccurrences` operation and return self.

        This method allows replacing a cluster on a device across all endpoints
        for the specified cluster types when the quirk is applied.
        """
        types = []
        if replace_server_instances:
            types.append(ClusterType.Server)
        if replace_client_instances:
            types.append(ClusterType.Client)
        self.replace_occurrences_ops.append(
            ReplaceClusterOccurrences(
                cluster=replacement_cluster_class,
                cluster_types=tuple(types),
            )
        )
        return self

    def adds_endpoint(
        self,
        endpoint_id: int,
        profile_id: int = zigpy.profiles.zha.PROFILE_ID,
        device_type: int = 0xFF,
    ) -> Self:
        """Add an `AddEndpoint` operation and return self."""
        self.adds_endpoint_ops.append(
            AddEndpoint(
                endpoint_id=endpoint_id,
                profile_id=profile_id,
                device_type=device_type,
            )
        )
        return self

    def removes_endpoint(self, endpoint_id: int) -> Self:
        """Add a `RemoveEndpoint` operation and return self."""
        self.removes_endpoint_ops.append(RemoveEndpoint(endpoint_id=endpoint_id))
        return self

    def replaces_endpoint(
        self,
        endpoint_id: int,
        profile_id: int = zigpy.profiles.zha.PROFILE_ID,
        device_type: int = 0xFF,
    ) -> Self:
        """Add a `ReplaceEndpoint` operation and return self."""
        self.replaces_endpoint_ops.append(
            ReplaceEndpoint(
                endpoint_id=endpoint_id,
                profile_id=profile_id,
                device_type=device_type,
            )
        )
        return self

    def enum(
        self,
        attribute_name: str,
        enum_class: type[Enum],
        cluster_id: int,
        cluster_type: ClusterType = ClusterType.Server,
        endpoint_id: int = 1,
        entity_platform: EntityPlatform = EntityPlatform.SELECT,
        entity_type: EntityType = EntityType.CONFIG,
        initially_disabled: bool = False,
        attribute_initialized_from_cache: bool = True,
        reporting_config: ReportingConfig | None = None,
        unique_id_suffix: str | None = None,
        translation_key: str | None = None,
        fallback_name: str | None = None,
        primary: bool | None = None,
        *,
        translation_placeholders: dict[str, str] | None = None,
    ) -> Self:
        """Add an EntityMetadata containing ZCLEnumMetadata and return self.

        This method allows exposing an enum based entity in Home Assistant.
        """
        self._add_entity_metadata(
            ZCLEnumMetadata(
                endpoint_id=endpoint_id,
                cluster_id=cluster_id,
                cluster_type=cluster_type,
                entity_platform=entity_platform,
                entity_type=entity_type,
                initially_disabled=initially_disabled,
                attribute_initialized_from_cache=attribute_initialized_from_cache,
                reporting_config=reporting_config,
                unique_id_suffix=unique_id_suffix,
                translation_key=translation_key,
                translation_placeholders=translation_placeholders or {},
                fallback_name=fallback_name,
                enum=enum_class,
                attribute_name=attribute_name,
                primary=primary,
            )
        )
        return self

    def sensor(
        self,
        attribute_name: str,
        cluster_id: int,
        cluster_type: ClusterType = ClusterType.Server,
        endpoint_id: int = 1,
        divisor: int = 1,
        multiplier: int = 1,
        suggested_display_precision: int = 1,
        entity_type: EntityType = EntityType.STANDARD,
        device_class: SensorDeviceClass | None = None,
        state_class: SensorStateClass | None = None,
        unit: str | None = None,
        initially_disabled: bool = False,
        attribute_initialized_from_cache: bool = True,
        attribute_converter: Callable[[Any], Any] | None = None,
        reporting_config: ReportingConfig | None = None,
        unique_id_suffix: str | None = None,
        translation_key: str | None = None,
        fallback_name: str | None = None,
        primary: bool | None = None,
        *,
        translation_placeholders: dict[str, str] | None = None,
    ) -> Self:
        """Add an EntityMetadata containing ZCLSensorMetadata and return self.

        This method allows exposing a sensor entity in Home Assistant.
        """
        self._add_entity_metadata(
            ZCLSensorMetadata(
                endpoint_id=endpoint_id,
                cluster_id=cluster_id,
                cluster_type=cluster_type,
                entity_platform=EntityPlatform.SENSOR,
                entity_type=entity_type,
                initially_disabled=initially_disabled,
                attribute_initialized_from_cache=attribute_initialized_from_cache,
                reporting_config=reporting_config,
                unique_id_suffix=unique_id_suffix,
                translation_key=translation_key,
                translation_placeholders=translation_placeholders or {},
                fallback_name=fallback_name,
                attribute_name=attribute_name,
                attribute_converter=attribute_converter,
                divisor=divisor,
                multiplier=multiplier,
                suggested_display_precision=suggested_display_precision,
                unit=unit,
                device_class=device_class,
                state_class=state_class,
                primary=primary,
            )
        )
        return self

    def switch(
        self,
        attribute_name: str,
        cluster_id: int,
        cluster_type: ClusterType = ClusterType.Server,
        endpoint_id: int = 1,
        force_inverted: bool = False,
        invert_attribute_name: str | None = None,
        off_value: int = 0,
        on_value: int = 1,
        entity_platform: EntityPlatform = EntityPlatform.SWITCH,
        entity_type: EntityType = EntityType.CONFIG,
        initially_disabled: bool = False,
        attribute_initialized_from_cache: bool = True,
        reporting_config: ReportingConfig | None = None,
        unique_id_suffix: str | None = None,
        translation_key: str | None = None,
        fallback_name: str | None = None,
        primary: bool | None = None,
        *,
        translation_placeholders: dict[str, str] | None = None,
    ) -> Self:
        """Add an EntityMetadata containing SwitchMetadata and return self.

        This method allows exposing a switch entity in Home Assistant.
        """
        self._add_entity_metadata(
            SwitchMetadata(
                endpoint_id=endpoint_id,
                cluster_id=cluster_id,
                cluster_type=cluster_type,
                entity_platform=entity_platform,
                entity_type=entity_type,
                initially_disabled=initially_disabled,
                attribute_initialized_from_cache=attribute_initialized_from_cache,
                reporting_config=reporting_config,
                unique_id_suffix=unique_id_suffix,
                translation_key=translation_key,
                translation_placeholders=translation_placeholders or {},
                fallback_name=fallback_name,
                attribute_name=attribute_name,
                force_inverted=force_inverted,
                invert_attribute_name=invert_attribute_name,
                off_value=off_value,
                on_value=on_value,
                primary=primary,
            )
        )
        return self

    def number(
        self,
        attribute_name: str,
        cluster_id: int,
        cluster_type: ClusterType = ClusterType.Server,
        endpoint_id: int = 1,
        min_value: float | None = None,
        max_value: float | None = None,
        step: float | None = None,
        unit: str | None = None,
        mode: str | None = None,
        multiplier: float | None = None,
        entity_type: EntityType = EntityType.CONFIG,
        device_class: NumberDeviceClass | None = None,
        initially_disabled: bool = False,
        attribute_initialized_from_cache: bool = True,
        reporting_config: ReportingConfig | None = None,
        unique_id_suffix: str | None = None,
        translation_key: str | None = None,
        fallback_name: str | None = None,
        primary: bool | None = None,
        *,
        translation_placeholders: dict[str, str] | None = None,
    ) -> Self:
        """Add an EntityMetadata containing NumberMetadata and return self.

        This method allows exposing a number entity in Home Assistant.
        """
        self._add_entity_metadata(
            NumberMetadata(
                endpoint_id=endpoint_id,
                cluster_id=cluster_id,
                cluster_type=cluster_type,
                entity_platform=EntityPlatform.NUMBER,
                entity_type=entity_type,
                initially_disabled=initially_disabled,
                attribute_initialized_from_cache=attribute_initialized_from_cache,
                reporting_config=reporting_config,
                unique_id_suffix=unique_id_suffix,
                translation_key=translation_key,
                translation_placeholders=translation_placeholders or {},
                fallback_name=fallback_name,
                attribute_name=attribute_name,
                min=min_value,
                max=max_value,
                step=step,
                unit=unit,
                mode=mode,
                multiplier=multiplier,
                device_class=device_class,
                primary=primary,
            )
        )
        return self

    def binary_sensor(
        self,
        attribute_name: str,
        cluster_id: int,
        cluster_type: ClusterType = ClusterType.Server,
        endpoint_id: int = 1,
        entity_type: EntityType = EntityType.DIAGNOSTIC,
        device_class: BinarySensorDeviceClass | None = None,
        initially_disabled: bool = False,
        attribute_initialized_from_cache: bool = True,
        attribute_converter: Callable[[Any], Any] | None = None,
        reporting_config: ReportingConfig | None = None,
        unique_id_suffix: str | None = None,
        translation_key: str | None = None,
        fallback_name: str | None = None,
        primary: bool | None = None,
        *,
        translation_placeholders: dict[str, str] | None = None,
    ) -> Self:
        """Add an EntityMetadata containing BinarySensorMetadata and return self.

        This method allows exposing a binary sensor entity in Home Assistant.
        """
        self._add_entity_metadata(
            BinarySensorMetadata(
                endpoint_id=endpoint_id,
                cluster_id=cluster_id,
                cluster_type=cluster_type,
                entity_platform=EntityPlatform.BINARY_SENSOR,
                entity_type=entity_type,
                initially_disabled=initially_disabled,
                attribute_initialized_from_cache=attribute_initialized_from_cache,
                reporting_config=reporting_config,
                unique_id_suffix=unique_id_suffix,
                translation_key=translation_key,
                translation_placeholders=translation_placeholders or {},
                fallback_name=fallback_name,
                attribute_name=attribute_name,
                attribute_converter=attribute_converter,
                device_class=device_class,
                primary=primary,
            )
        )
        return self

    def write_attr_button(
        self,
        attribute_name: str,
        attribute_value: int,
        cluster_id: int,
        cluster_type: ClusterType = ClusterType.Server,
        endpoint_id: int = 1,
        entity_type: EntityType = EntityType.CONFIG,
        initially_disabled: bool = False,
        attribute_initialized_from_cache: bool = True,
        unique_id_suffix: str | None = None,
        translation_key: str | None = None,
        fallback_name: str | None = None,
        primary: bool | None = None,
        *,
        translation_placeholders: dict[str, str] | None = None,
    ) -> Self:
        """Add an EntityMetadata containing WriteAttributeButtonMetadata and return self.

        This method allows exposing a button entity in Home Assistant that writes
        a value to an attribute when pressed.
        """
        self._add_entity_metadata(
            WriteAttributeButtonMetadata(
                endpoint_id=endpoint_id,
                cluster_id=cluster_id,
                cluster_type=cluster_type,
                entity_platform=EntityPlatform.BUTTON,
                entity_type=entity_type,
                initially_disabled=initially_disabled,
                attribute_initialized_from_cache=attribute_initialized_from_cache,
                unique_id_suffix=unique_id_suffix,
                translation_key=translation_key,
                translation_placeholders=translation_placeholders or {},
                fallback_name=fallback_name,
                attribute_name=attribute_name,
                attribute_value=attribute_value,
                primary=primary,
            )
        )
        return self

    def command_button(
        self,
        command_name: str,
        cluster_id: int,
        command_args: tuple | None = None,
        command_kwargs: dict[str, Any] | None = None,
        cluster_type: ClusterType = ClusterType.Server,
        endpoint_id: int = 1,
        entity_type: EntityType = EntityType.CONFIG,
        initially_disabled: bool = False,
        unique_id_suffix: str | None = None,
        translation_key: str | None = None,
        fallback_name: str | None = None,
        primary: bool | None = None,
        *,
        translation_placeholders: dict[str, str] | None = None,
    ) -> Self:
        """Add an EntityMetadata containing ZCLCommandButtonMetadata and return self.

        This method allows exposing a button entity in Home Assistant that executes
        a ZCL command when pressed.
        """
        self._add_entity_metadata(
            ZCLCommandButtonMetadata(
                endpoint_id=endpoint_id,
                cluster_id=cluster_id,
                cluster_type=cluster_type,
                entity_platform=EntityPlatform.BUTTON,
                entity_type=entity_type,
                initially_disabled=initially_disabled,
                unique_id_suffix=unique_id_suffix,
                translation_key=translation_key,
                translation_placeholders=translation_placeholders or {},
                fallback_name=fallback_name,
                command_name=command_name,
                args=command_args if command_args is not None else (),
                kwargs=command_kwargs if command_kwargs is not None else frozendict(),
                primary=primary,
            )
        )
        return self

    def device_automation_triggers(
        self, device_automation_triggers: dict[tuple[str, str], dict[str, str]]
    ) -> Self:
        """Add device automation triggers and returns self."""
        self.device_automation_triggers_metadata.update(device_automation_triggers)
        return self

    def friendly_name(self, *, model: str, manufacturer: str) -> Self:
        """Rename the device."""
        self.friendly_name_metadata = FriendlyNameMetadata(
            model=model, manufacturer=manufacturer
        )
        return self

    def exposes_feature(
        self, feature: str, config: dict[str, Any] | None = None
    ) -> Self:
        """Add an exposed feature."""
        self.exposes_features.append(
            ExposesFeatureMetadata(feature=feature, config=config or {})
        )
        return self

    def device_alert(self, *, level: DeviceAlertLevel, message: str) -> Self:
        """Add a device alert."""
        self.device_alerts.append(DeviceAlertMetadata(level=level, message=message))
        return self

    def prevent_default_entity_creation(
        self,
        *,
        endpoint_id: int | None = None,
        cluster_id: int | None = None,
        cluster_type: ClusterType | None = None,
        unique_id_suffix: str | None = None,
        function: Callable[[Any], bool] | None = None,
    ) -> Self:
        """Do not create default entities."""
        if cluster_id is not None and cluster_type is None:
            cluster_type = ClusterType.Server

        self.disabled_default_entities.append(
            PreventDefaultEntityCreationMetadata(
                endpoint_id=endpoint_id,
                cluster_id=cluster_id,
                cluster_type=cluster_type,
                unique_id_suffix=unique_id_suffix,
                function=function,
            ),
        )
        return self

    def change_entity_metadata(
        self,
        *,
        endpoint_id: int | None = None,
        cluster_id: int | None = None,
        cluster_type: ClusterType | None = None,
        unique_id_suffix: str | None = None,
        function: Callable[[Any], bool] | None = None,
        new_primary: bool | None = None,
        new_unique_id: str | None = None,
        new_translation_key: str | None = None,
        new_translation_placeholders: dict[str, str] | None = None,
        new_device_class: (
            BinarySensorDeviceClass | NumberDeviceClass | SensorDeviceClass | None
        ) = None,
        new_state_class: SensorStateClass | None = None,
        new_entity_category: EntityType | None = None,
        new_entity_registry_enabled_default: bool | None = None,
        new_fallback_name: str | None = None,
    ) -> Self:
        """Change entity metadata for matching entities."""
        if cluster_id is not None and cluster_type is None:
            cluster_type = ClusterType.Server

        self.changed_entity_metadata.append(
            ChangedEntityMetadata(
                endpoint_id=endpoint_id,
                cluster_id=cluster_id,
                cluster_type=cluster_type,
                unique_id_suffix=unique_id_suffix,
                function=function,
                new_primary=new_primary,
                new_unique_id=new_unique_id,
                new_translation_key=new_translation_key,
                new_translation_placeholders=new_translation_placeholders,
                new_device_class=new_device_class,
                new_state_class=new_state_class,
                new_entity_category=new_entity_category,
                new_entity_registry_enabled_default=new_entity_registry_enabled_default,
                new_fallback_name=new_fallback_name,
            ),
        )
        return self

    def _compile_transformations(self) -> tuple[DeviceOp, ...]:
        """Compile the accumulated cluster/endpoint operations, in v2 order."""
        ops: list[DeviceOp] = []

        if self.device_node_descriptor is not None:
            ops.append(SetNodeDescriptor(node_descriptor=self.device_node_descriptor))

        # endpoints need to be modified before clusters
        ops.extend(self.removes_endpoint_ops)
        ops.extend(self.adds_endpoint_ops)
        ops.extend(self.replaces_endpoint_ops)
        ops.extend(self.removes_ops)
        ops.extend(self.adds_ops)
        ops.extend(self.replaces_ops)
        ops.extend(self.replace_occurrences_ops)

        return tuple(ops)

    def add_to_registry(
        self, registry: DeviceRegistry | None = None
    ) -> QuirkRegistryEntry:
        """Compile the quirk into a `QuirkRegistryEntry` and register it."""
        if not self.manufacturer_model_metadata:
            raise ValueError(
                "At least one manufacturer and model must be specified for a v2 quirk."
            )

        device_match = DeviceMatch(
            applies_to=tuple(self.manufacturer_model_metadata),
            filters=tuple(self.filters),
            firmware_version_min=self.firmware_version_min,
            firmware_version_max=self.firmware_version_max,
            firmware_version_allow_missing=self.firmware_version_allow_missing,
        )

        manufacturer, model = self.manufacturer_model_metadata[0]

        # Legacy `quirk_class` identity, now carried as provenance data.
        quirk_label = f"({manufacturer} / {model})"

        quirk_definition = QuirkDefinition(
            friendly_name=self.friendly_name_metadata,
            exposes_features=tuple(self.exposes_features),
            device_alerts=tuple(self.device_alerts),
            disabled_default_entities=tuple(self.disabled_default_entities),
            changed_entity_metadata=tuple(self.changed_entity_metadata),
            entity_metadata=tuple(self.entity_metadata),
            device_automation_triggers=self.device_automation_triggers_metadata,
            skip_configuration=self.skip_device_configuration,
        )

        # Shared QuirkV2Device (or custom subclass) bound to this definition; no subclass minted.
        base = self.custom_device_class if self.custom_device_class else QuirkV2Device
        zha_device_factory = QuirkV2Factory(base, quirk_definition)

        # Clone the interviewed device (the first transform) before applying
        # modifications, so the bare device is left intact for persistence.
        clone = ReplaceZigpyDevice(self.custom_zigpy_device_class)

        ops = self._compile_transformations()

        # Stamp the triggers onto the resolved zigpy device (matching v1 quirks,
        # where they are a class attribute) so consumers reading only the zigpy
        # device — e.g. HA's early device trigger cache — see them too.
        if quirk_definition.device_automation_triggers:
            ops = (
                *ops,
                SetDeviceAutomationTriggers(
                    triggers=quirk_definition.device_automation_triggers
                ),
            )

        zigpy_transforms = (clone, *ops)

        entry = QuirkRegistryEntry(
            device_match=device_match,
            zigpy_transforms=zigpy_transforms,
            zha_device_factory=zha_device_factory,
            source=QuirkSource(
                module=self.quirk_module,
                file=str(self.quirk_file),
                line=self.quirk_file_line,
                label=quirk_label,
            ),
        )

        (registry or self.registry).register(entry)

        return entry

    def clone(self, omit_man_model_data: bool = True) -> Self:
        """Clone this QuirkBuilder potentially omitting manufacturer and model data."""
        new_builder = deepcopy(self)
        new_builder.registry = self.registry
        if omit_man_model_data:
            new_builder.manufacturer_model_metadata = []
        return new_builder
