"""Centralite module for custom device handlers."""
import logging

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.clusters.general import PowerConfiguration

_LOGGER = logging.getLogger(__name__)
CENTRALITE = "CentraLite"


class PowerConfigurationCluster(CustomCluster, PowerConfiguration):
    """Centralite power configuration cluster."""

    cluster_id = PowerConfiguration.cluster_id
    BATTERY_VOLTAGE_ATTR = 0x0020
    BATTERY_PERCENTAGE_REMAINING = 0x0021
    MIN_VOLTS = 21
    MAX_VOLTS = 31
    VOLTS_TO_PERCENT = {
        31: 100,
        30: 90,
        29: 80,
        28: 70,
        27: 60,
        26: 50,
        25: 40,
        24: 30,
        23: 20,
        22: 10,
        21: 0,
    }

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == self.BATTERY_VOLTAGE_ATTR:
            super()._update_attribute(
                self.BATTERY_PERCENTAGE_REMAINING,
                self._calculate_battery_percentage(value),
            )

    def _calculate_battery_percentage(self, raw_value):
        volts = raw_value
        if raw_value < self.MIN_VOLTS:
            volts = self.MIN_VOLTS
        elif raw_value > self.MAX_VOLTS:
            volts = self.MAX_VOLTS

        percent = self.VOLTS_TO_PERCENT.get(volts, -1)
        if percent != -1:
            percent = percent * 2
        return percent


class CentraLiteAccelCluster(CustomCluster):
    """Centralite acceleration cluster."""

    cluster_id = 0xFC02
    name = "CentraLite Accelerometer"
    ep_attribute = "accelerometer"
    attributes = {
        0x0000: ("motion_threshold_multiplier", t.uint8_t),
        0x0002: ("motion_threshold", t.uint16_t),
        0x0010: ("acceleration", t.bitmap8),  # acceleration detected
        0x0012: ("x_axis", t.int16s),
        0x0013: ("y_axis", t.int16s),
        0x0014: ("z_axis", t.int16s),
    }

    client_commands = {}
    server_commands = {}
