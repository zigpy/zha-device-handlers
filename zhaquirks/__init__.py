"""Quirks implementations for the ZHA component of Homeassistant."""
import logging
import importlib
import pkgutil

from zigpy.quirks import CustomCluster
import zigpy.types as types
from zigpy.util import ListenableMixin
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zdo import types as zdotypes

from .const import (
    ATTRIBUTE_ID,
    ATTRIBUTE_NAME,
    COMMAND_ATTRIBUTE_UPDATED,
    UNKNOWN,
    VALUE,
    ZHA_SEND_EVENT,
)

_LOGGER = logging.getLogger(__name__)


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
        if (
            self.server_commands is not None
            and self.server_commands.get(command_id) is not None
        ):
            self.listener_event(
                ZHA_SEND_EVENT, self, self.server_commands.get(command_id)[0], args
            )

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        self.listener_event(
            ZHA_SEND_EVENT,
            self,
            COMMAND_ATTRIBUTE_UPDATED,
            {
                ATTRIBUTE_ID: attrid,
                ATTRIBUTE_NAME: self.attributes.get(attrid, [UNKNOWN])[0],
                VALUE: value,
            },
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
            dstaddr,
        )


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


class PowerConfigurationCluster(CustomCluster, PowerConfiguration):
    """Common use power configuration cluster."""

    cluster_id = PowerConfiguration.cluster_id
    BATTERY_VOLTAGE_ATTR = 0x0020
    BATTERY_PERCENTAGE_REMAINING = 0x0021
    MIN_VOLTS = 15  # old 2.1
    MAX_VOLTS = 28  # old 3.2

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == self.BATTERY_VOLTAGE_ATTR:
            super()._update_attribute(
                self.BATTERY_PERCENTAGE_REMAINING,
                self._calculate_battery_percentage(value),
            )

    def _calculate_battery_percentage(self, raw_value):

        # V     New     Old
        # 28:   100     100
        # 27:   92.3    100
        # 26:   84.6    100
        # 25:   76.9    90
        # 24:   69.2    90
        # 23:   61.5    70
        # 22:   53.8    70
        # 21:   46.1    50
        # 20:   38.4    50
        # 19:   30.7    30
        # 18:   23.0    30
        # 17:   15.3    15
        # 16:   7.6     1
        # 15:   0       0

        volts = raw_value
        max_volts = self.MAX_VOLTS
        min_volts = self.MIN_VOLTS

        # Calculate the percentage
        percent = (volts - min_volts) / (max_volts - min_volts)
        percent = round(percent * 100, 1)

        # Ensure > 0, battery reporting so not dead
        if (percent <= 0):
            percent = 1

        # Ensure < 100, set return value
        percent = min(100, percent)

        log_msg = (
            f"Voltage [RAW]:{raw_value} [Max]:{max_volts} "
            f"[Min]:{min_volts}, Battery Percent: {percent}"
        )
        _LOGGER.debug(log_msg)

        # ZHA reports in range of 200%?!
        percent = percent * 2

        return percent


NAME = __name__
PATH = __path__
for importer, modname, ispkg in pkgutil.walk_packages(path=PATH, prefix=NAME + "."):
    importlib.import_module(modname)
