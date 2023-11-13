"""Module for Legrand devices."""

from zigpy.quirks import CustomCluster
import zigpy.types as t

from zhaquirks import PowerConfigurationCluster

LEGRAND = "Legrand"
MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xFC01  # decimal = 64513


class LegrandCluster(CustomCluster):
    """LegrandCluster."""

    cluster_id = MANUFACTURER_SPECIFIC_CLUSTER_ID
    name = "LegrandCluster"
    ep_attribute = "legrand_cluster"
    attributes = {
        0x0000: ("dimmer", t.data16, True),
        0x0001: ("led_dark", t.Bool, True),
        0x0002: ("led_on", t.Bool, True),
    }


class LegrandPowerConfigurationCluster(PowerConfigurationCluster):
    """PowerConfiguration conversor 'V --> %' for Legrand devices."""

    MIN_VOLTS = 2.5
    MAX_VOLTS = 3.0
