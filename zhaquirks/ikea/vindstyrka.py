"""Device handler for IKEA of Sweden VINDSTYRKA Air quality sensor."""

from typing import Dict

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    Ota,
    PollControl,
)
from zigpy.zcl.clusters.hvac import Fan
from zigpy.zcl.clusters.measurement import (
    PM25,
    RelativeHumidity,
    TemperatureMeasurement,
)
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.ikea import IKEA, IKEA_CLUSTER_ID, WWAH_CLUSTER_ID


class VOCIndex(CustomCluster):
    """VOC index value as reported by the Senserion SEN54 inside VINDSTYRKA."""

    cluster_id: t.uint16_t = 0xFC7E
    name: str = "VOC Index"
    ep_attribute: str = "voc_index"

    attributes: Dict[t.uint16_t, ZCLAttributeDef] = {
        0x0000: ZCLAttributeDef(
            "measured_value", type=t.Single, access="rp", mandatory=True
        ),
        0x0001: ZCLAttributeDef(
            "min_measured_value", type=t.Single, access="r", mandatory=True
        ),
        0x0002: ZCLAttributeDef(
            "max_measured_value", type=t.Single, access="r", mandatory=True
        ),
    }


class IkeaVINDSTYRKA(CustomDevice):
    """IKEA of Sweden VINDSTYRKA Air quality sensor."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [(IKEA, "VINDSTYRKA"), (IKEA, "VINDSTYRKA")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=770
            # device_version=0
            # input_clusters=[0, 3, 4, 1026, 1029, 1066, 64599, 64636, 64638]
            # output_clusters=[3, 25, 32, 514]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,  # 260
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,  # 0x0302
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0x0000
                    Identify.cluster_id,  # 0x0003
                    Groups.cluster_id,  # 0x0004
                    TemperatureMeasurement.cluster_id,  # 0x0402
                    RelativeHumidity.cluster_id,  # 0x0405
                    PM25.cluster_id,  # 0x042a
                    WWAH_CLUSTER_ID,  # 0xfc57
                    IKEA_CLUSTER_ID,  # 0xfc7c
                    VOCIndex.cluster_id,  # 0xfc7e
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,  # 0x0003
                    Ota.cluster_id,  # 0x0019
                    PollControl.cluster_id,  # 0x0020
                    Fan.cluster_id,  # 0x0202
                ],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # device_version=0
            # input_clusters=[]
            # output_clusters=[33]>
            242: {
                PROFILE_ID: 0xA1E0,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],  # 0x0021
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,  # 260
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,  # 0x0302
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0x0000
                    Identify.cluster_id,  # 0x0003
                    Groups.cluster_id,  # 0x0004
                    TemperatureMeasurement.cluster_id,  # 0x0402
                    RelativeHumidity.cluster_id,  # 0x0405
                    PM25.cluster_id,  # 0x042a
                    WWAH_CLUSTER_ID,  # 0xfc57
                    IKEA_CLUSTER_ID,  # 0xfc7c
                    VOCIndex,  # 0xfc7e
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,  # 0x0003
                    Ota.cluster_id,  # 0x0019
                    PollControl.cluster_id,  # 0x0020
                    Fan.cluster_id,  # 0x0202
                ],
            },
            242: {
                PROFILE_ID: 0xA1E0,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],  # 0x0021
            },
        },
    }
