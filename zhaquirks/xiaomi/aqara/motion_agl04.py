"""Quirk for LUMI lumi.motion.agl04."""
from __future__ import annotations

import logging
from typing import Any

from zigpy.profiles import zha
import zigpy.types as types
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PowerConfiguration
from zigpy.zcl.clusters.measurement import OccupancySensing

from zhaquirks import Bus, LocalDataCluster
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
    MotionCluster,
    OccupancyCluster,
    XiaomiAqaraE1Cluster,
    XiaomiCustomDevice,
    XiaomiPowerConfiguration,
)

OCCUPANCY = 0
ON = 1
MOTION_ATTRIBUTE = 274
DETECTION_INTERVAL = 0x0102
MOTION_SENSITIVITY = 0x010C
_LOGGER = logging.getLogger(__name__)


class OppleCluster(XiaomiAqaraE1Cluster):
    """Opple cluster."""

    ep_attribute = "opple_cluster"
    attributes = {
        DETECTION_INTERVAL: ("detection_interval", types.uint8_t, True),
        MOTION_SENSITIVITY: ("motion_sensitivity", types.uint8_t, True),
    }

    def _update_attribute(self, attrid: int, value: Any) -> None:
        super()._update_attribute(attrid, value)
        if attrid == MOTION_ATTRIBUTE:
            self.endpoint.occupancy.update_attribute(OCCUPANCY, ON)

    async def write_attributes(
        self, attributes: dict[str | int, Any], manufacturer: int | None = None
    ) -> list:
        """Write attributes to device with internal 'attributes' validation."""
        result = await super().write_attributes(attributes, manufacturer)
        interval = attributes.get(
            "detection_interval", attributes.get(DETECTION_INTERVAL)
        )
        _LOGGER.debug("interval: %s", interval)
        if interval is not None:
            self.endpoint.ias_zone.reset_s = int(interval)
        return result


class LocalOccupancyCluster(LocalDataCluster, OccupancyCluster):
    """Local occupancy cluster."""


class LocalMotionCluster(MotionCluster):
    """Local motion cluster."""

    reset_s: int = 60


class LumiLumiMotionAgl04(XiaomiCustomDevice):
    """Lumi lumi.motion.agl04 custom device implementation."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.battery_size = 11
        self.battery_quantity = 2
        self.illuminance_bus = Bus()
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
