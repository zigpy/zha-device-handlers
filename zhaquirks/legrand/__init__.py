"""Module for Legrand devices."""

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks import PowerConfigurationCluster

LEGRAND = "Legrand"
MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xFC01  # decimal = 64513


class LegrandCluster(CustomCluster):
    """LegrandCluster."""

    cluster_id = MANUFACTURER_SPECIFIC_CLUSTER_ID
    name = "LegrandCluster"
    ep_attribute = "legrand_cluster"

    class AttributeDefs(BaseAttributeDefs):
        """Cluster attributes."""

        dimmer = ZCLAttributeDef(
            id=0x0000, type=t.data16, is_manufacturer_specific=True
        )
        led_dark = ZCLAttributeDef(
            id=0x0001, type=t.Bool, is_manufacturer_specific=True
        )
        led_on = ZCLAttributeDef(id=0x0002, type=t.Bool, is_manufacturer_specific=True)


class LegrandPowerConfigurationCluster(PowerConfigurationCluster):
    """PowerConfiguration conversor 'V --> %' for Legrand devices."""

    MIN_VOLTS = 2.5
    MAX_VOLTS = 3.0
