"""Device-cloning machinery for quirks."""

from __future__ import annotations

import typing

from zigpy.const import (
    SIG_ENDPOINTS,
    SIG_EP_INPUT,
    SIG_EP_OUTPUT,
    SIG_EP_PROFILE,
    SIG_EP_TYPE,
    SIG_MANUFACTURER,
    SIG_MODEL,
    SIG_NODE_DESC,
    SIG_SKIP_CONFIG,
)
import zigpy.device
import zigpy.endpoint
import zigpy.types as t
from zigpy.zdo import ZDO

from zhaquirks.clusters import CustomCluster

if typing.TYPE_CHECKING:
    from zigpy.application import ControllerApplication


class BaseCustomDevice(zigpy.device.Device):
    """Base class for custom devices."""

    _copy_cluster_attr_cache = False
    replacement: dict[str, typing.Any] = {}

    def __init__(
        self,
        application: ControllerApplication,
        ieee: t.EUI64,
        nwk: t.NWK,
        replaces: zigpy.device.Device,
    ) -> None:
        """Initialize the custom device, cloning state from `replaces`."""
        super().__init__(application, ieee, nwk)

        self.lqi = replaces.lqi
        self.rssi = replaces.rssi
        self.last_seen = replaces.last_seen
        self.relays = replaces.relays
        self.original_signature = replaces.original_signature

        def set_device_attr(attr):
            if attr in self.replacement:
                setattr(self, attr, self.replacement[attr])
            else:
                setattr(self, attr, getattr(replaces, attr))

        set_device_attr("status")
        set_device_attr(SIG_NODE_DESC)
        set_device_attr(SIG_MANUFACTURER)
        set_device_attr(SIG_MODEL)
        set_device_attr(SIG_SKIP_CONFIG)
        for endpoint_id in self.replacement.get(SIG_ENDPOINTS, {}):
            self.add_endpoint(endpoint_id, replace_device=replaces)

    def add_endpoint(
        self, endpoint_id: int, replace_device: zigpy.device.Device | None = None
    ) -> zigpy.endpoint.Endpoint:
        """Add an endpoint, cloning it from the replaced device."""

        # The clone path requires a device to clone from. A quirk transform that adds an
        # endpoint at runtime (e.g. `adds_endpoint`) calls this without one, so fall
        # back to a plain endpoint it can then configure itself.
        if replace_device is None or endpoint_id not in self.replacement.get(
            SIG_ENDPOINTS, {}
        ):
            return super().add_endpoint(endpoint_id)

        endpoints = self.replacement[SIG_ENDPOINTS]

        if isinstance(endpoints[endpoint_id], tuple):
            custom_ep_type = endpoints[endpoint_id][0]
            replacement_data = endpoints[endpoint_id][1]
        else:
            custom_ep_type = CustomEndpoint
            replacement_data = endpoints[endpoint_id]

        ep = custom_ep_type(self, endpoint_id, replacement_data, replace_device)
        self.endpoints[endpoint_id] = ep
        return ep

    async def apply_custom_configuration(self, *args, **kwargs):
        """Apply custom configuration to the device's custom clusters."""
        for endpoint in self.endpoints.values():
            if isinstance(endpoint, ZDO):
                continue
            for cluster in endpoint.in_clusters.values():
                if (
                    isinstance(cluster, CustomCluster)
                    and cluster.apply_custom_configuration
                    != CustomCluster.apply_custom_configuration
                ):
                    await cluster.apply_custom_configuration(*args, **kwargs)
            for cluster in endpoint.out_clusters.values():
                if (
                    isinstance(cluster, CustomCluster)
                    and cluster.apply_custom_configuration
                    != CustomCluster.apply_custom_configuration
                ):
                    await cluster.apply_custom_configuration(*args, **kwargs)


class CustomZigpyDevice(BaseCustomDevice):
    """A faithful 1:1 clone of a device whose low-level behavior can be overridden."""

    _copy_cluster_attr_cache = True

    def __init__(
        self,
        application: ControllerApplication,
        ieee: t.EUI64,
        nwk: t.NWK,
        replaces: zigpy.device.Device,
    ) -> None:
        """Initialize the clone, mirroring `replaces`' endpoints and clusters."""
        self.replacement = {
            SIG_ENDPOINTS: {
                key: {
                    SIG_EP_PROFILE: endpoint.profile_id,
                    SIG_EP_TYPE: endpoint.device_type,
                    SIG_EP_INPUT: [
                        cluster.cluster_id for cluster in endpoint.in_clusters.values()
                    ],
                    SIG_EP_OUTPUT: [
                        cluster.cluster_id for cluster in endpoint.out_clusters.values()
                    ],
                }
                for key, endpoint in replaces.endpoints.items()
                if not isinstance(endpoint, ZDO)
            }
        }
        super().__init__(application, ieee, nwk, replaces)


class CustomEndpoint(zigpy.endpoint.Endpoint):
    """Custom endpoint implementation for quirks."""

    def __init__(
        self,
        device: BaseCustomDevice,
        endpoint_id: int,
        replacement_data: dict[str, typing.Any],
        replace_device: zigpy.device.Device,
    ) -> None:
        """Initialize the endpoint from the quirk's replacement data."""
        super().__init__(device, endpoint_id)

        def set_device_attr(attr):
            if attr in replacement_data:
                setattr(self, attr, replacement_data[attr])
            else:
                setattr(self, attr, getattr(replace_device[endpoint_id], attr))

        set_device_attr(SIG_EP_PROFILE)
        set_device_attr(SIG_EP_TYPE)
        self.status = zigpy.endpoint.Status.ZDO_INIT

        for c in replacement_data.get(SIG_EP_INPUT, []):
            if isinstance(c, int):
                cluster = None
                cluster_id = c
            else:
                cluster = c(self, is_server=True)
                cluster_id = cluster.cluster_id
            cluster = self.add_input_cluster(cluster_id, cluster)
            if self.device._copy_cluster_attr_cache:
                if (
                    endpoint_id in replace_device.endpoints
                    and cluster_id in replace_device.endpoints[endpoint_id].in_clusters
                ):
                    cluster._attr_cache_internal = (
                        replace_device[endpoint_id]
                        .in_clusters[cluster_id]
                        ._attr_cache.clone(cluster)
                    )

        for c in replacement_data.get(SIG_EP_OUTPUT, []):
            if isinstance(c, int):
                cluster = None
                cluster_id = c
            else:
                cluster = c(self, is_server=False)
                cluster_id = cluster.cluster_id
            cluster = self.add_output_cluster(cluster_id, cluster)
            if self.device._copy_cluster_attr_cache:
                if (
                    endpoint_id in replace_device.endpoints
                    and cluster_id in replace_device.endpoints[endpoint_id].out_clusters
                ):
                    cluster._attr_cache_internal = (
                        replace_device[endpoint_id]
                        .out_clusters[cluster_id]
                        ._attr_cache.clone(cluster)
                    )
