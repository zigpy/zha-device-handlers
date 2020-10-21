"""Xiaomi aqara contact sensor device."""
import logging

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
)

from .. import LUMI, BasicCluster, PowerConfigurationCluster, XiaomiCustomDevice
from ...const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SKIP_CONFIGURATION,
)

OPEN_CLOSE_DEVICE_TYPE = 0x5F01
XIAOMI_CLUSTER_ID = 0xFFFF

_LOGGER = logging.getLogger(__name__)


class Magnet(XiaomiCustomDevice):
    """Xiaomi mija contact sensor device."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.battery_size = 11
        super().__init__(*args, **kwargs)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=260
        #  device_version=1
        #  input_clusters=[0, 3, 65535, 25]
        #  output_clusters=[0, 4, 3, 6, 8, 5, 25]>
        MODELS_INFO: [(LUMI, "lumi.sensor_magnet")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    BasicCluster.cluster_id,
                    Identify.cluster_id,
                    XIAOMI_CLUSTER_ID,
                    Ota.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    BasicCluster.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Scenes.cluster_id,
                    Ota.cluster_id,
                ],
            }
        },
    }

    replacement = {
        SKIP_CONFIGURATION: True,
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SENSOR,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    Identify.cluster_id,
                    PowerConfigurationCluster,
                    XIAOMI_CLUSTER_ID,
                    Ota.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    BasicCluster,
                    OnOff.cluster_id,
                    Groups.cluster_id,
                    Identify.cluster_id,
                    LevelControl.cluster_id,
                    Scenes.cluster_id,
                    Ota.cluster_id,
                ],
            }
        },
    }
