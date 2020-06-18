"""Quirk for Xiaomi Aqara Smart LED bulb ZNLDP12LM."""
import logging

from zigpy.profiles import zha
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import (
    AnalogOutput,
    Groups,
    Identify,
    LevelControl,
    MultistateOutput,
    OnOff,
    Ota,
    PowerConfiguration,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.measurement import (
    OccupancySensing,
    PressureMeasurement,
    RelativeHumidity,
    TemperatureMeasurement,
)

from .. import LUMI, BasicCluster, XiaomiCustomDevice
from ... import CustomCluster
from ...const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

_LOGGER = logging.getLogger(__name__)


class LightAqcn02(XiaomiCustomDevice):
    """Custom device for ZNLDP12LM."""

    class ColorCluster(CustomCluster, Color):
        """Color Cluster."""

        _CONSTANT_ATTRIBUTES = {0x400A: 0x0010, 0x400B: 153, 0x400C: 370}

    signature = {
        # endpoint=1 profile=260 device_type=258 device_version=1 input_clusters=[0, 4, 3, 5, 10, 258, 13, 19, 6, 1, 1030, 8, 768, 1027, 1029, 1026] output_clusters=[25, 10, 13, 258, 19, 6, 1, 1030, 8, 768]>
        MODELS_INFO: [(LUMI, "lumi.light.aqcn02")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    BasicCluster.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Time.cluster_id,
                    AnalogOutput.cluster_id,
                    MultistateOutput.cluster_id,
                    WindowCovering.cluster_id,
                    Color.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    PressureMeasurement.cluster_id,
                    RelativeHumidity.cluster_id,
                    OccupancySensing.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    PowerConfiguration.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Time.cluster_id,
                    AnalogOutput.cluster_id,
                    MultistateOutput.cluster_id,
                    Ota.cluster_id,
                    WindowCovering.cluster_id,
                    ColorCluster.cluster_id,
                    OccupancySensing.cluster_id,
                ],
            }
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    BasicCluster,  # 0
                    Groups.cluster_id,  # 4
                    Identify.cluster_id,  # 3
                    Scenes.cluster_id,  # 5
                    OnOff.cluster_id,  # 6
                    PowerConfiguration.cluster_id,  # 1
                    LevelControl.cluster_id,  # 8
                    ColorCluster,  # 768
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,  # 10
                    Ota.cluster_id,  # 19
                    OccupancySensing.cluster_id,  # 1030
                ],
            }
        }
    }
