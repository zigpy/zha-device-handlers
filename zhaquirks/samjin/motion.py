"""Samjin/Aeotec motion sensor quirk."""

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    Ota,
    PollControl,
    PowerConfiguration,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.const import (
    COMMAND,
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.samjin import SAMJIN
from zhaquirks.smartthings import SmartThingsIasZone

# Device automation trigger constants
COMMAND_MOTION_DETECTED = "motion_detected"
COMMAND_MOTION_CLEARED = "motion_cleared"
MOTION_DETECTED = "motion_detected"
MOTION_CLEARED = "motion_cleared"


class SamjinPowerConfiguration(CustomCluster, PowerConfiguration):
    """Samjin PowerConfiguration cluster with battery percentage correction.

    Samjin devices report battery_percentage_remaining with a non-linear scale.
    This cluster applies the SmartThings correction formula to get accurate readings.

    Formula from SmartThings driver:
        corrected = rawValue - (200 - rawValue) / 2

    Also falls back to voltage-based calculation if percentage not reported.
    CR2 battery voltage range: 2.1V (depleted) to 3.0V (fresh)
    """

    # Battery voltage thresholds for fallback calculation
    MIN_VOLTS = 2.1
    MAX_VOLTS = 3.0

    # Attribute ID for battery percentage
    BATTERY_PERCENTAGE_REMAINING = 0x0021
    BATTERY_VOLTAGE = 0x0020

    def _update_attribute(self, attrid, value):
        """Apply Samjin battery correction formula to percentage reports."""
        if attrid == self.BATTERY_PERCENTAGE_REMAINING and value is not None:
            # Apply SmartThings correction formula for Samjin devices
            # Formula: corrected = rawValue - (200 - rawValue) / 2
            corrected = value - (200 - value) // 2
            # Clamp to valid range (0-200 per ZCL spec)
            corrected = max(0, min(200, corrected))
            value = corrected

        super()._update_attribute(attrid, value)

        # If we got voltage but no percentage, calculate from voltage
        if attrid == self.BATTERY_VOLTAGE and value is not None:
            if self._attr_cache.get(self.BATTERY_PERCENTAGE_REMAINING) is None:
                # Convert from 100mV units to volts and calculate percentage
                volts = value / 10.0
                percent = (volts - self.MIN_VOLTS) / (self.MAX_VOLTS - self.MIN_VOLTS)
                percent = max(0.0, min(1.0, percent))
                calculated = int(percent * 200)
                super()._update_attribute(self.BATTERY_PERCENTAGE_REMAINING, calculated)


class SamjinMotion(CustomDevice):
    """Samjin/Aeotec Motion Sensor (GP-AEOMSSUS / GP-U999SJVLBAA)."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        # device_version=0
        # input_clusters=[0, 1, 3, 32, 1026, 1280, 2821]
        # output_clusters=[3, 25]>
        MODELS_INFO: [(SAMJIN, "motion")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    SamjinPowerConfiguration,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    SmartThingsIasZone,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            }
        }
    }

    # Device automation triggers for Home Assistant UI
    device_automation_triggers = {
        (MOTION_DETECTED, MOTION_DETECTED): {COMMAND: COMMAND_MOTION_DETECTED},
        (MOTION_CLEARED, MOTION_CLEARED): {COMMAND: COMMAND_MOTION_CLEARED},
    }
