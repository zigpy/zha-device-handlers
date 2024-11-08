"""Konke motion sensor."""

import math

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PowerConfiguration
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.measurement import IlluminanceMeasurement
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import Bus, MotionWithReset, PowerConfigurationCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.konke import KONKE, MotionCluster, OccupancyCluster

KONKE_CLUSTER_ID = 0xFCC0


class IlluminanceMeasurementCluster(CustomCluster, IlluminanceMeasurement):
    """Terncy Illuminance Measurement Cluster."""

    ATTR_ID = 0

    def _update_attribute(self, attrid, value):
        if attrid == self.ATTR_ID and value > 0:
            value = 10000 * math.log10(value) + 1
        super()._update_attribute(attrid, value)


class MotionClusterC(MotionWithReset):
    """Motion cluster."""

    reset_s: int = 60


class KonkeMotion(CustomDevice):
    """Custom device representing konke motion sensors."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.occupancy_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        #  device_version=0
        #  input_clusters=[0, 1, 3, 1280, 64704]
        #  output_clusters=[3, 64704]>
        MODELS_INFO: [
            (KONKE, "3AFE28010402000D"),
            (KONKE, "3AFE14010402000D"),
            (KONKE, "3AFE27010402000D"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    IasZone.cluster_id,
                    KONKE_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, KONKE_CLUSTER_ID],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    OccupancyCluster,
                    MotionCluster,
                    KONKE_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, KONKE_CLUSTER_ID],
            }
        }
    }


class KonkeMotionB(CustomDevice):
    """Custom device representing konke motion sensors."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.occupancy_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        #  device_version=0
        #  input_clusters=[0, 1, 3, 1280]
        #  output_clusters=[3]>
        MODELS_INFO: [
            (KONKE, "3AFE28010402000D"),
            (KONKE, "3AFE14010402000D"),
            (KONKE, "3AFE27010402000D"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    IasZone.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    OccupancyCluster,
                    MotionCluster,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id],
            }
        }
    }


class KonkeMotionC(CustomDevice):
    """Custom device representing konke motion sensors."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.occupancy_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=0x0104 device_type=0x0402
        #  device_version=0
        #  input_clusters=[0, 1, 3, 1280, 2821, 64704]
        #  output_clusters=[25, 64704]>
        MODELS_INFO: [
            (KONKE, "3AFE08010402100D"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    PowerConfiguration.cluster_id,  # 1
                    Identify.cluster_id,  # 3
                    IasZone.cluster_id,  # 1280
                    Diagnostic.cluster_id,  # 2821
                    KONKE_CLUSTER_ID,  # 64704
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, KONKE_CLUSTER_ID],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    MotionClusterC,
                    Diagnostic.cluster_id,
                    KONKE_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, KONKE_CLUSTER_ID],
            }
        }
    }


class KonkeMotionD(CustomDevice):
    """Custom device representing konke motion sensors."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.occupancy_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=0x0104 device_type=0x0402
        #  device_version=0
        #  input_clusters=[0, 3, 1024, 1280, 2821, 64704]
        #  output_clusters=[0, 25, 64704]>
        MODELS_INFO: [
            (KONKE, "3AFE13010402020D"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    Identify.cluster_id,  # 3
                    IlluminanceMeasurement.cluster_id,  # 400
                    IasZone.cluster_id,  # 500
                    Diagnostic.cluster_id,
                    KONKE_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Basic.cluster_id, Ota.cluster_id, KONKE_CLUSTER_ID],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    Identify.cluster_id,  # 3
                    IlluminanceMeasurementCluster,
                    IasZone.cluster_id,  # 500
                    Diagnostic.cluster_id,
                    KONKE_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Basic.cluster_id, Ota.cluster_id, KONKE_CLUSTER_ID],
            }
        }
    }
