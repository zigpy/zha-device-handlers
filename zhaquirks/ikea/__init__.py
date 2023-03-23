"""Ikea module."""
import logging

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import PowerConfiguration, Scenes
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks import DoublingPowerConfigurationCluster

_LOGGER = logging.getLogger(__name__)

IKEA = "IKEA of Sweden"
IKEA_CLUSTER_ID = 0xFC7C  # decimal = 64636
WWAH_CLUSTER_ID = 0xFC57  # decimal = 64599 ('Works with all Hubs' cluster)

# PowerConfiguration cluster attributes
BATTERY_VOLTAGE = PowerConfiguration.attributes_by_name["battery_voltage"]
BATTERY_SIZES = PowerConfiguration.attributes_by_name["battery_size"]
BATTERY_QUANTITY = PowerConfiguration.attributes_by_name["battery_quantity"]
BATTERY_RATED_VOLTAGE = PowerConfiguration.attributes_by_name["battery_rated_voltage"]


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

    server_commands = Scenes.server_commands.copy()
    server_commands.update(
        {
            0x0007: foundation.ZCLCommandDef(
                "press",
                {"param1": t.int16s, "param2": t.int8s, "param3": t.int8s},
                False,
                is_manufacturer_specific=True,
            ),
            0x0008: foundation.ZCLCommandDef(
                "hold",
                {"param1": t.int16s, "param2": t.int8s},
                False,
                is_manufacturer_specific=True,
            ),
            0x0009: foundation.ZCLCommandDef(
                "release",
                {
                    "param1": t.int16s,
                },
                False,
                is_manufacturer_specific=True,
            ),
        }
    )


# ZCL compliant IKEA power configuration clusters:


class PowerConfig2AAACluster(PowerConfiguration):
    """Updating power attributes 2 AAA."""

    _CONSTANT_ATTRIBUTES = {
        BATTERY_SIZES: 4,
        BATTERY_QUANTITY: 2,
        BATTERY_RATED_VOLTAGE: 15,
    }


class PowerConfig2CRCluster(PowerConfiguration):
    """Updating power attributes 2 CR2032."""

    _CONSTANT_ATTRIBUTES = {
        BATTERY_SIZES: 10,
        BATTERY_QUANTITY: 2,
        BATTERY_RATED_VOLTAGE: 30,
    }


class PowerConfig1CRCluster(PowerConfiguration):
    """Updating power attributes 1 CR2032."""

    _CONSTANT_ATTRIBUTES = {
        BATTERY_SIZES: 10,
        BATTERY_QUANTITY: 1,
        BATTERY_RATED_VOLTAGE: 30,
    }


class PowerConfig1CRXCluster(PowerConfiguration):
    """Updating power attributes 1 CR2032 and zero voltage."""

    _CONSTANT_ATTRIBUTES = {
        BATTERY_VOLTAGE: 0,
        BATTERY_SIZES: 10,
        BATTERY_QUANTITY: 1,
        BATTERY_RATED_VOLTAGE: 30,
    }


# doubling IKEA power configuration clusters:


class DoublingPowerConfig2AAACluster(
    DoublingPowerConfigurationCluster, PowerConfig2AAACluster
):
    """Doubling power configuration cluster. Updating power attributes 2 AAA."""


class DoublingPowerConfig2CRCluster(
    DoublingPowerConfigurationCluster, PowerConfig2CRCluster
):
    """Doubling power configuration cluster. Updating power attributes 2 CR2032."""


class DoublingPowerConfig1CRCluster(
    DoublingPowerConfigurationCluster, PowerConfig1CRCluster
):
    """Doubling power configuration cluster. Updating power attributes 1 CR2032."""


class DoublingPowerConfig1CRXCluster(
    DoublingPowerConfigurationCluster, PowerConfig1CRXCluster
):
    """Doubling power configuration cluster. Updating power attributes 1 CR2032 and zero voltage."""
