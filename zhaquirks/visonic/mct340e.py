"""Visonic MCT340E device."""
import logging

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PollControl
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import PowerConfigurationCluster

from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

OSRAM_DEVICE = 0x0810  # 2064 base 10
OSRAM_CLUSTER = 0xFD00  # 64768 base 10


_LOGGER = logging.getLogger(__name__)

DIAGNOSTICS_CLUSTER_ID = 0x0B05  # decimal = 2821


class CustomPowerConfigurationCluster(PowerConfigurationCluster):
    """Custom PowerConfigurationCluster."""

    cluster_id = PowerConfigurationCluster.cluster_id
    MIN_VOLTS = 2.1
    MAX_VOLTS = 3.0


class MCT340E(CustomDevice):
    """Visonic MCT340E device."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        # device_version=0
        # input_clusters=[0, 1, 3, 1026, 1280, 32, 2821]
        # output_clusters=[25]>
        MODELS_INFO: [("Visonic", "MCT-340 E")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    CustomPowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                    PollControl.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    CustomPowerConfigurationCluster,
                    Identify.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                    PollControl.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        }
    }
