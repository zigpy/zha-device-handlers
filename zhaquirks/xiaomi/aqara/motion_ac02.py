"""Quirk for LUMI lumi.motion.ac02."""

from __future__ import annotations

from zigpy import types
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PowerConfiguration

from zhaquirks import Bus, LocalDataCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    BatterySize,
)
from zhaquirks.xiaomi import (
    LocalIlluminanceMeasurementCluster,
    MotionCluster,
    OccupancyCluster,
    XiaomiMotionManufacturerCluster,
    XiaomiPowerConfiguration,
)

MOTION_ATTRIBUTE = 274
DETECTION_INTERVAL = 0x0102
MOTION_SENSITIVITY = 0x010C
TRIGGER_INDICATOR = 0x0152


class OppleCluster(XiaomiMotionManufacturerCluster):
    """Xiaomi manufacturer cluster.

    This uses the shared XiaomiMotionManufacturerCluster implementation
    which parses motion and illuminance reports from Xiaomi devices.
    """

    attributes = {
        DETECTION_INTERVAL: ("detection_interval", types.uint8_t, True),
        MOTION_SENSITIVITY: ("motion_sensitivity", types.uint8_t, True),
        TRIGGER_INDICATOR: ("trigger_indicator", types.uint8_t, True),
    }


class IlluminanceMeasurementClusterP1(LocalIlluminanceMeasurementCluster):
    """Local illuminance measurement cluster that also discards more invalid values sent by this device."""

    def _update_attribute(self, attrid, value):
        if attrid == self.AttributeDefs.measured_value.id and (
            value < 0 or value > 0xFFDC
        ):
            self.debug(
                "Received invalid illuminance value: %s - setting illuminance to 0",
                value,
            )
            value = 0
        super()._update_attribute(attrid, value)


class LocalOccupancyCluster(LocalDataCluster, OccupancyCluster):
    """Local occupancy cluster."""


class LocalMotionCluster(MotionCluster):
    """Local motion cluster."""

    reset_s: int = 30

    @property
    def reset_after(self) -> int:
        """Use the device's `detection_interval` if known, else `reset_s`."""
        interval = self.endpoint.opple_cluster.get("detection_interval")
        if interval is None:
            return self.reset_s
        return int(interval)


class LumiMotionAC02(CustomDevice):
    """Lumi lumi.motion.ac02 (RTCGQ14LM) custom device implementation."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.battery_size = BatterySize.CR1632
        self.battery_quantity = 2
        self.motion_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [("LUMI", "lumi.motion.ac02")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    OppleCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                    OppleCluster.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    XiaomiPowerConfiguration,
                    Identify.cluster_id,
                    LocalOccupancyCluster,
                    LocalMotionCluster,
                    IlluminanceMeasurementClusterP1,
                    OppleCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                    OppleCluster,
                ],
            }
        }
    }
