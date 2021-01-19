"""Device handler for Terncy knob smart dimmer."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    Ota,
    PollControl,
    PowerConfiguration,
)

from zhaquirks import DoublingPowerConfigurationCluster

from . import BUTTON_TRIGGERS, KNOB_TRIGGERS, TerncyRawCluster
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

TERNCY_KNOB_DEVICE_TYPE = 0x01F2


class TerncyKnobSmartDimmer(CustomDevice):
    """Terncy knob smart dimmer."""

    signature = {
        MODELS_INFO: [("Xiaoyan", "TERNCY-SD01"), (None, "TERNCY-SD01")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=498
            # device_version=0 input_clusters=[0, 1, 3, 32, 64716]
            # output_clusters=[25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: TERNCY_KNOB_DEVICE_TYPE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TerncyRawCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DoublingPowerConfigurationCluster,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TerncyRawCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        }
    }

    device_automation_triggers = {**BUTTON_TRIGGERS, **KNOB_TRIGGERS}
