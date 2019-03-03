
import logging

from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.quirks import CustomDevice, CustomCluster
import zigpy.types as t

_LOGGER = logging.getLogger(__name__)


class PowerConfigurationCluster(CustomCluster, PowerConfiguration):
    cluster_id = PowerConfiguration.cluster_id
    BATTERY_VOLTAGE_ATTR = 0x0020
    BATTERY_PERCENTAGE_REMAINING = 0x0021
    MIN_VOLTS = 15
    MAX_VOLTS = 28
    VOLTS_TO_PERCENT = {
        28: 100,
        27: 100,
        26: 100,
        25: 90,
        24: 90,
        23: 70,
        22: 70,
        21: 50,
        20: 50,
        19: 30,
        18: 30,
        17: 15,
        16: 1,
        15: 0
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == self.BATTERY_VOLTAGE_ATTR:
            super()._update_attribute(
                self.BATTERY_PERCENTAGE_REMAINING,
                self._calculate_battery_percentage(value)
            )

    def _calculate_battery_percentage(self, rawValue):
        volts = rawValue
        if rawValue < self.MIN_VOLTS:
            volts = self.MIN_VOLTS
        elif rawValue > self.MAX_VOLTS:
            volts = self.MAX_VOLTS

        return self.VOLTS_TO_PERCENT.get(volts, 'unknown')


class CentraLiteAccelCluster(CustomCluster):
    cluster_id = 0xfc02
    name = "CentraLite Accelerometer"
    ep_attribute = 'accelerometer'
    attributes = {
        0x0000: ('motion_threshold_multiplier', t.uint8_t),
        0x0002: ('motion_threshold', t.uint16_t),
        0x0010: ('acceleration', t.bitmap8),  # acceleration detected
        0x0012: ('x_axis', t.int16s),
        0x0013: ('y_axis', t.int16s),
        0x0014: ('z_axis', t.int16s),
    }

    client_commands = {}
    server_commands = {}
