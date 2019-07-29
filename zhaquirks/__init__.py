"""Quirks implementations for the ZHA component of Homeassistant."""
import importlib
import pkgutil

from zigpy.quirks import CustomCluster
import zigpy.types as types
from zigpy.util import ListenableMixin
from zigpy.zdo import types as zdotypes
from zigpy.zcl.clusters.general import PowerConfiguration

UNKNOWN = 'Unknown'


class Bus(ListenableMixin):
    """Event bus implementation."""

    def __init__(self, *args, **kwargs):
        """Init event bus."""
        super().__init__(*args, **kwargs)
        self._listeners = {}


class LocalDataCluster(CustomCluster):
    """Cluster meant to prevent remote calls."""

    async def read_attributes_raw(self, attributes, manufacturer=None):
        """Prevent remote reads."""
        attributes = [types.uint16_t(a) for a in attributes]
        values = [self._attr_cache.get(attr) for attr in attributes]
        return values


class EventableCluster(CustomCluster):
    """Cluster that generates events."""

    def handle_cluster_request(self, tsn, command_id, args):
        """Send cluster requests as events."""
        if self.server_commands is not None and\
                self.server_commands.get(command_id) is not None:
            self.listener_event(
                'zha_send_event',
                self,
                self.server_commands.get(command_id)[0],
                args
            )

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        self.listener_event(
            'zha_send_event',
            self,
            'attribute_updated',
            {
                'attribute_id': attrid,
                'attribute_name': self.attributes.get(attrid, [UNKNOWN])[0],
                'value': value
            }
        )


class GroupBoundCluster(CustomCluster):
    """
    Cluster that can only bind to a group instead of direct to hub.

    Binding this cluster results in binding to a group that the coordinator
    is a member of.
    """

    COORDINATOR_GROUP_ID = 0x30  # Group id with only coordinator as a member

    async def bind(self):
        """Bind cluster to a group."""
        # Ensure coordinator is a member of the group
        application = self._endpoint.device.application
        coordinator = application.get_device(application.ieee)
        await coordinator.add_to_group(self.COORDINATOR_GROUP_ID)

        # Bind cluster to group
        dstaddr = zdotypes.MultiAddress()
        dstaddr.addrmode = 1
        dstaddr.nwk = self.COORDINATOR_GROUP_ID
        dstaddr.endpoint = self._endpoint.endpoint_id
        return await self._endpoint.device.zdo.Bind_req(
            self._endpoint.device.ieee,
            self._endpoint.endpoint_id,
            self.cluster_id,
            dstaddr)


class DoublingPowerConfigurationCluster(CustomCluster, PowerConfiguration):
    """PowerConfiguration cluster implementation.

    This implementation doubles battery pct remaining for non standard devices
    that don't follow the reporting spec.
    """

    cluster_id = PowerConfiguration.cluster_id
    BATTERY_PERCENTAGE_REMAINING = 0x0021

    def _update_attribute(self, attrid, value):
        if attrid == self.BATTERY_PERCENTAGE_REMAINING:
            value = value * 2
        super()._update_attribute(attrid, value)


NAME = __name__
PATH = __path__
for importer, modname, ispkg in pkgutil.walk_packages(
        path=PATH,
        prefix=NAME + '.'
        ):
    importlib.import_module(modname)
