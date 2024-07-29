"""XHS2-UE Door/Window Sensor."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PollControl
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import PowerConfigurationCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class CustomPowerConfigurationCluster(PowerConfigurationCluster):
    """Custom PowerConfigurationCluster."""

    MIN_VOLTS = 2.1
    MAX_VOLTS = 3.0


class ContactSensor(CustomDevice):
    """XHS2-UE Door/Window Sensor."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        # device_version=0
        # input_clusters=[0, 1, 3, 1026, 1280, 32, 2821]
        # output_clusters=[25]>
        MODELS_INFO: [("Universal Electronics Inc", "URC4460BC0-X-R")],
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
                    Diagnostic.cluster_id,
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
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        }
    }
