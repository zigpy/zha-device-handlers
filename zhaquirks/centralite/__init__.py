"""Centralite module for custom device handlers."""
import logging

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.clusters.general import PowerConfiguration

_LOGGER = logging.getLogger(__name__)
CENTRALITE = "CentraLite"


class PowerConfigurationCluster(CustomCluster, PowerConfiguration):
    """Centralite 2.8-1.5V power configuration cluster."""

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
        15: 0,
    }

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == self.BATTERY_VOLTAGE_ATTR:
            super()._update_attribute(
                self.BATTERY_PERCENTAGE_REMAINING,
                self._new_battery_percentage(value),
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


    def _new_battery_percentage(self, raw_value):
        """Checks Manufacturer and returns appropriate battery percent."""
        # Todo: get values
        device_manufacturer = "SmartThings"

        if (device_manufacturer in ("SmartThings", "CentraLite")):
            return_pct = self._smartthings_battery(raw_value)
        else:
            return_pct = self._other_battery(raw_value)

        return return_pct

    def _smartthings_battery(self, raw_value):
        """Returns battery percent for 2.8-1.5v."""
        volts = raw_value # For the battery_map to work the key needs to be an int

        battery_map = {
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

        min_volts = 15
        max_volts = 28

        if (volts < min_volts):
            volts = min_volts
        elif (volts > max_volts):
            volts = max_volts

        pct = battery_map[volts]

        log_msg = f"Voltage [RAW]:{raw_value} [Determined]:{volts} [Max]:{max_volts} [Min]:{min_volts}, Battery Percent: {pct}"
        _LOGGER.debug(log_msg)

        return pct

    def _other_battery(self, raw_value):
        """Returns battery percent for [3.0|2.7]-2.1v."""
        # Make sure value is a float. 2.2 vice 22
        # This may not be necessary in the future.
        # Added for testing
        volts = raw_value
        if int(raw_value):
            volts /= 10.

        # Todo: get values
        current_battery_pct = None
        last_volts = None

        # Setup some defaults
        use_old_batt = self.should_use_old_battery_reporting()
        min_volts = 2.1

        if (use_old_batt):
            max_volts = 3.0
        else:
            max_volts = 2.7

        # Get the current battery percentage as a multiplier 0 - 1
        #cur_val_volts = Integer.parseInt(device.currentState("battery")?.value ?: "100") / 100.0
        if (current_battery_pct):
            value = int(current_battery_pct)
        else:
            value = int("100")
        cur_val_volts = value / 100.0

        # Find the corresponding voltage from our range
        cur_val_volts = cur_val_volts * (max_volts - min_volts) + min_volts

        # Round to the nearest 10th of a volt
        cur_val_volts = round(10 * cur_val_volts, 1) / 10.0

        # Only update the battery reading if we don't have a last reading,
        # OR we have received the same reading twice in a row
        # OR we don't currently have a battery reading
        # OR the value we just received is at least 2 steps off from the last reported value
        # OR the device's firmware is older than 1.15.7
        if (
            use_old_batt or
            last_volts is None or
            last_volts == volts or
            current_battery_pct is None or
            abs(cur_val_volts - volts) > 0.1
        ):

            # Calculate the percentage
            pct = (volts - min_volts) / (max_volts - min_volts)
            rounded_pct = round(pct * 100, 1)

            # Ensure > 0
            if (rounded_pct <= 0):
                rounded_pct = 1

            # Ensure < 100, set return value
            return_pct = min(100, rounded_pct)

        else:
            # Don't update as we want to smooth the battery values,
            # but do report the last battery state for record keeping purposes
            return_pct = current_battery_pct

        log_msg = f"Voltage [RAW]:{raw_value} [Determined]:{volts} [Max]:{max_volts} [Min]:{min_volts}, Battery Percent: {return_pct}"
        _LOGGER.debug(log_msg)

        return return_pct

    def should_use_old_battery_reporting(self):
        """Requires firmware version info."""
        # https://github.com/SmartThingsCommunity/SmartThingsPublic/blob/77351e6babc03c3c9651030833c7d29e0aaee563/devicetypes/smartthings/smartsense-multi-sensor.src/smartsense-multi-sensor.groovy#L492-L509
        return False


class PowerConfigurationCluster31(CustomCluster, PowerConfiguration):
    """Centralite 3.1-2.1V power configuration cluster."""

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
