"""Device handler for Bosch ISWZDL1WP11G motion sensor."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PollControl
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import PowerConfigurationCluster

from . import BOSCH
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class BoschWP11GPowerConfiguration(PowerConfigurationCluster):
    """Bosch power configuration cluster for ISWZDL1WP11G motion sensor."""

    MAX_VOLTS = 6.0
    MIN_VOLTS = 3.0


class ISWZDL1WP11G(CustomDevice):
    """Custom device representing Bosch ISWZDL1WP11G motion sensor."""

    signature = {
        #  <SimpleDescriptor endpoint=5 profile=260 device_type=1026
        #  device_version=0
        #  input_clusters=[0, 1, 3, 32, 1026, 1280, 2821]
        #  output_clusters=[25]>
        MODELS_INFO: [(BOSCH, "ISW-ZDL1-WP11G")],
        ENDPOINTS: {
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            5: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    BoschWP11GPowerConfiguration,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        }
    }
