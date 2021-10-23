"""Ikea module."""
import logging

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.clusters.general import Scenes, PowerConfiguration
from zigpy.zcl.clusters.lightlink import LightLink

_LOGGER = logging.getLogger(__name__)
IKEA = "IKEA of Sweden"
ROTATED = "device_rotated"


class LightLinkCluster(CustomCluster, LightLink):
    """Ikea LightLink cluster."""

    async def bind(self):
        """Bind LightLink cluster to coordinator."""
        application = self._endpoint.device.application
        try:
            coordinator = application.get_device(application.ieee)
        except KeyError:
            _LOGGER.warning("Aborting - unable to locate required coordinator device.")
            return
        group_list = await self.get_group_identifiers(0)
        try:
            group_record = group_list[2]
            group_id = group_record[0].group_id
        except IndexError:
            _LOGGER.warning(
                "unable to locate required group info - falling back to group 0x0000."
            )
            group_id = 0x0000
        status = await coordinator.add_to_group(
            group_id,
            name="Default Lightlink Group",
        )
        return [status]


class ScenesCluster(CustomCluster, Scenes):
    """Ikea Scenes cluster."""

    manufacturer_server_commands = {
        0x0007: ("press", (t.int16s, t.int8s, t.int8s), False),
        0x0008: ("hold", (t.int16s, t.int8s), False),
        0x0009: ("release", (t.int16s,), False),
    }


class PowerConfiguration2AAACluster(CustomCluster, PowerConfiguration):
    """PowerConfiguration cluster implementation.
    This implementation doubles battery pct remaining for non standard devices
    that don't follow the reporting spec and fixing 2 AAA."""

    cluster_id = PowerConfiguration.cluster_id
    BATTERY_PERCENTAGE_REMAINING = 0x0021
    BATTERY_SIZES = 0x0031
    BATTERY_QUANTITY = 0x0033
    BATTERY_RATED_VOLTAGE = 0x0034

    _CONSTANT_ATTRIBUTES = {
        BATTERY_SIZES: 4,
        BATTERY_RATED_VOLTAGE: 15,
        BATTERY_QUANTITY: 2,
    }

    def _update_attribute(self, attrid, value):
        if attrid == self.BATTERY_PERCENTAGE_REMAINING:
            value = value * 2
        super()._update_attribute(attrid, value)


class PowerConfiguration2CRCluster(CustomCluster, PowerConfiguration):
    """PowerConfiguration cluster implementation.
    This implementation doubles battery pct remaining for non standard devices
    that don't follow the reporting spec and fixing 2 CR."""

    cluster_id = PowerConfiguration.cluster_id
    BATTERY_PERCENTAGE_REMAINING = 0x0021
    BATTERY_SIZES = 0x0031
    BATTERY_QUANTITY = 0x0033
    BATTERY_RATED_VOLTAGE = 0x0034

    _CONSTANT_ATTRIBUTES = {
        BATTERY_SIZES: 10,
        BATTERY_RATED_VOLTAGE: 30,
        BATTERY_QUANTITY: 2,
    }

    def _update_attribute(self, attrid, value):
        if attrid == self.BATTERY_PERCENTAGE_REMAINING:
            value = value * 2
        super()._update_attribute(attrid, value)


class PowerConfiguration1CRCluster(CustomCluster, PowerConfiguration):
    """PowerConfiguration cluster implementation.
    This implementation doubles battery pct remaining for non standard devices
    that don't follow the reporting spec and fixing 1 CR."""

    cluster_id = PowerConfiguration.cluster_id
    BATTERY_PERCENTAGE_REMAINING = 0x0021
    BATTERY_SIZES = 0x0031
    BATTERY_QUANTITY = 0x0033
    BATTERY_RATED_VOLTAGE = 0x0034

    _CONSTANT_ATTRIBUTES = {
        BATTERY_SIZES: 10,
        BATTERY_RATED_VOLTAGE: 30,
        BATTERY_QUANTITY: 1,
    }

    def _update_attribute(self, attrid, value):
        if attrid == self.BATTERY_PERCENTAGE_REMAINING:
            value = value * 2
        super()._update_attribute(attrid, value)


class PowerConfiguration1CRXCluster(CustomCluster, PowerConfiguration):
    """PowerConfiguration cluster implementation.
    This implementation doubles battery pct remaining for non standard devices
    that don't follow the reporting spec and fixing 1 CR and BV."""

    cluster_id = PowerConfiguration.cluster_id
    BATTERY_VOLTAGE = 0x0020
    BATTERY_PERCENTAGE_REMAINING = 0x0021
    BATTERY_SIZES = 0x0031
    BATTERY_QUANTITY = 0x0033
    BATTERY_RATED_VOLTAGE = 0x0034

    _CONSTANT_ATTRIBUTES = {
        BATTERY_SIZES: 10,
        BATTERY_VOLTAGE: 0,
        BATTERY_RATED_VOLTAGE: 30,
        BATTERY_SIZES: 10,
        BATTERY_QUANTITY: 1,
        BATTERY_RATED_VOLTAGE: 30,
    }

    def _update_attribute(self, attrid, value):
        if attrid == self.BATTERY_PERCENTAGE_REMAINING:
            value = value * 2
        super()._update_attribute(attrid, value)
