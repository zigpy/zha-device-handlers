"""Xiaomi Mija smoke detector quirks implementations."""
import logging

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    AnalogInput,
    Identify,
    MultistateInput,
    Ota,
    PowerConfiguration,
)
from zigpy.zcl.clusters.security import IasZone

from .. import BasicCluster, PowerConfigurationCluster, XiaomiCustomDevice
from ...const import DEVICE_TYPE, ENDPOINTS, INPUT_CLUSTERS, OUTPUT_CLUSTERS, PROFILE_ID

IAS_ZONE = 0x0402
_LOGGER = logging.getLogger(__name__)


class MijiaHoneywellSmokeDetectorSensor(XiaomiCustomDevice):
    """MijiaHoneywellSmokeDetectorSensor custom device."""

    def __init__(self, *args, **kwargs):
        """Init method."""
        self.battery_size = 8  # CR123a
        super().__init__(*args, **kwargs)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        #  device_version=
        #  input_clusters=[0, 1, 3, 12, 18, 1280]
        #  output_clusters=[25]>
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: IAS_ZONE,
                INPUT_CLUSTERS: [
                    BasicCluster.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    AnalogInput.cluster_id,
                    MultistateInput.cluster_id,
                    IasZone.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        }
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    BasicCluster,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    AnalogInput.cluster_id,
                    MultistateInput.cluster_id,
                    IasZone.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        }
    }
