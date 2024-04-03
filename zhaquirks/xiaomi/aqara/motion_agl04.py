"""Quirk for LUMI lumi.motion.agl04."""
from __future__ import annotations

from typing import Any

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
)
from zhaquirks.xiaomi import (
    DeviceTemperatureCluster,
    LocalOccupancyCluster,
    MotionCluster,
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

    async def write_attributes(
        self, attributes: dict[str | int, Any], manufacturer: int | None = None
    ) -> list:
        """Write attributes to device with internal 'attributes' validation."""
        result = await super().write_attributes(attributes, manufacturer)
        interval = attributes.get(
            "detection_interval", attributes.get(DETECTION_INTERVAL)
        )
        self.endpoint.device.debug("occupancy reset interval: %s", interval)
        if interval is not None:
            self.endpoint.ias_zone.reset_s = int(interval)
        return result


class LocalMotionCluster(MotionCluster):
    """Local motion cluster."""

    reset_s: int = 60


class LumiLumiMotionAgl04(XiaomiCustomDevice):
    """Lumi lumi.motion.agl04 custom device implementation."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.battery_size = 11
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
                    LocalOccupancyCluster,
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
