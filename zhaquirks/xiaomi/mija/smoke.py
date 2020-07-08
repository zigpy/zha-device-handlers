"""Xiaomi Mija smoke detector quirks implementations.

Manufacturer ID: 0x115F
Known Options for set_options:
High Sensitivity: 0x04010000,
Medium Sensitivity: 0x04020000,
Low Sensitivity: 0x04030000,
Self Test: 0x03010000

Responses from get_status:
High Sensitivity: 0x0101000011010003,
Medium Sensitivity: 0x0102000011010003,
Low Sensitivity: 0x0103000011010003.
"""
import logging

from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    AnalogInput,
    Identify,
    MultistateInput,
    Ota,
    PowerConfiguration,
)
from zigpy.zcl.clusters.security import IasZone

from .. import BasicCluster, PowerConfigurationCluster, XiaomiCustomDevice
from ... import CustomCluster
from ...const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SKIP_CONFIGURATION,
)

IAS_ZONE = 0x0402

_LOGGER = logging.getLogger(__name__)


class XiaomiSmokeIASCluster(CustomCluster, IasZone):
    """Xiaomi smoke IAS cluster implementation."""

    manufacturer_attributes = {
        0xFFF1: ("set_options", t.uint32_t),
        0xFFF0: ("get_status", t.uint32_t),
    }


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
        SKIP_CONFIGURATION: True,
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    BasicCluster,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    AnalogInput.cluster_id,
                    MultistateInput.cluster_id,
                    XiaomiSmokeIASCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }
