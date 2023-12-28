"""Xiaomi aqara P1 contact sensor device."""

from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Identify, OnOff, Ota, PowerConfiguration
from zigpy.zcl.clusters.security import IasZone

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
    XiaomiAqaraE1Cluster,
    XiaomiCustomDevice,
    XiaomiPowerConfigurationPercent,
)


class OppleCluster(XiaomiAqaraE1Cluster):
    """Opple cluster."""

    class DetectionDistance(t.enum8):
        """Detection distance."""

        TenMillimeters = 0x01
        TwentyMillimeters = 0x02
        ThirtyMillimeters = 0x03

    attributes = {
        0x010C: ("detection_distance", t.uint8_t, True),
    }


class LumiMagnetAC01(XiaomiCustomDevice):
    """Custom device representing lumi.magnet.ac01."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.battery_size = 8
        super().__init__(*args, **kwargs)

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        # device_version=1
        # input_clusters=[0, 1, 3, 1280]
        # output_clusters=[25]>
        MODELS_INFO: [(LUMI, "lumi.magnet.ac01")],
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
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    BasicCluster,
                    XiaomiPowerConfigurationPercent,
                    Identify.cluster_id,
                    OppleCluster,
                ],
                OUTPUT_CLUSTERS: [OnOff.cluster_id, Ota.cluster_id],
            },
        },
    }
