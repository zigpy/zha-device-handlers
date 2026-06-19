"""Quirk for LUMI lumi.motion.agl04."""

from __future__ import annotations

from zigpy import types
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PowerConfiguration
from zigpy.zcl.clusters.measurement import OccupancySensing

from zhaquirks import Bus
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
    DeviceTemperatureCluster,
    MotionCluster,
    OccupancyCluster,
    XiaomiAqaraE1Cluster,
    XiaomiCustomDevice,
    XiaomiPowerConfiguration,
)

DETECTION_INTERVAL = 0x0102
MOTION_SENSITIVITY = 0x010C


class OppleCluster(XiaomiAqaraE1Cluster):
    """Opple cluster."""

    attributes = {
        DETECTION_INTERVAL: ("detection_interval", types.uint8_t, True),
        MOTION_SENSITIVITY: ("motion_sensitivity", types.uint8_t, True),
    }


class LocalMotionCluster(MotionCluster):
    """Local motion cluster."""

    reset_s: int = 60

    @property
    def reset_after(self) -> int:
        """Use the device's `detection_interval` if known, else `reset_s`."""
        interval = self.endpoint.opple_cluster.get(DETECTION_INTERVAL)
        if interval is None:
            return self.reset_s
        return int(interval)


class LumiLumiMotionAgl04(XiaomiCustomDevice):
    """Lumi lumi.motion.agl04 custom device implementation."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.battery_size = BatterySize.CR1632
        self.battery_quantity = 2
        self.motion_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [("LUMI", "lumi.motion.agl04")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    OccupancySensing.cluster_id,
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
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    XiaomiPowerConfiguration,
                    Identify.cluster_id,
                    DeviceTemperatureCluster,
                    OccupancyCluster,
                    LocalMotionCluster,
                    OppleCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            }
        }
    }
