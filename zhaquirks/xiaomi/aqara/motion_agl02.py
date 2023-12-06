"""Xiaomi aqara T1 motion sensor device."""
from __future__ import annotations

import zigpy
from zigpy.profiles import zha
from zigpy.typing import AddressingMode
from zigpy.zcl.clusters.general import Identify, Ota
from zigpy.zcl.clusters.measurement import IlluminanceMeasurement, OccupancySensing

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
    LUMI,
    BasicCluster,
    IlluminanceMeasurementCluster,
    MotionCluster,
    OccupancyCluster,
    XiaomiAqaraE1Cluster,
    XiaomiCustomDevice,
    XiaomiPowerConfiguration,
)

XIAOMI_CLUSTER_ID = 0xFCC0


class XiaomiManufacturerCluster(XiaomiAqaraE1Cluster):
    """Xiaomi manufacturer cluster."""

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == 274:
            value = value - 65536
            self.endpoint.illuminance.update_attribute(
                IlluminanceMeasurement.AttributeDefs.measured_value.id, value
            )
            self.endpoint.occupancy.update_attribute(
                OccupancySensing.AttributeDefs.occupancy.id,
                OccupancySensing.Occupancy.Occupied,
            )


class LocalOccupancyCluster(LocalDataCluster, OccupancyCluster):
    """Local occupancy cluster."""

    def handle_cluster_general_request(
        self,
        hdr: zigpy.zcl.foundation.ZCLHeader,
        args: list,
        *,
        dst_addressing: AddressingMode | None = None,
    ) -> None:
        """Ignore occupancy attribute reports on this cluster, as they're invalid and sent by the sensor every hour."""


class MotionT1(XiaomiCustomDevice):
    """Xiaomi motion sensor device."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.battery_size = 11
        self.motion_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=263
        #  device_version=1
        #  input_clusters=[0, 1, 3, 1030]
        #  output_clusters=[3, 19]>
        MODELS_INFO: [(LUMI, "lumi.motion.agl02")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    BasicCluster.cluster_id,
                    XiaomiPowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    OccupancySensing.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    BasicCluster,
                    XiaomiPowerConfiguration,
                    Identify.cluster_id,
                    LocalOccupancyCluster,
                    MotionCluster,
                    IlluminanceMeasurementCluster,
                    XiaomiManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        },
    }
