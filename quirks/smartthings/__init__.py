
import logging

from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.quirks import CustomCluster


_LOGGER = logging.getLogger(__name__)


class PowerConfigurationCluster(CustomCluster, PowerConfiguration):
    cluster_id = PowerConfiguration.cluster_id
    BATTERY_VOLTAGE_ATTR = 0x0020
    BATTERY_PERCENTAGE_REMAINING = 0x0021
    MIN_VOLTS = 15
    MAX_VOLTS = 28

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _update_attribute(self, attrid, value):
        if attrid == self.BATTERY_VOLTAGE_ATTR:
            super()._update_attribute(
                self.BATTERY_PERCENTAGE_REMAINING,
                self._calculate_battery_percentage(value)
            )
        else:
            super()._update_attribute(attrid, value)

    def _calculate_battery_percentage(self, rawValue):
        battery_percent = round((rawValue * 100 - self.MIN_VOLTS) /
                                (self.MAX_VOLTS - self.MIN_VOLTS) * 100)
        if battery_percent > 100:
            battery_percent = 100
        elif battery_percent < 0:
            battery_percent = 0
        return battery_percent
