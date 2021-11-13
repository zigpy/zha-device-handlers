"""Device handler for eWeLink WB01."""
import logging

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, OnOff, PowerConfiguration

from zhaquirks.const import (
    BUTTON,
    COMMAND,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_TOGGLE,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
)

_LOGGER = logging.getLogger(__name__)


class SonoffButton(CustomDevice):
    """Custom device representing sonoff devices."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=0 device_version=0
        # input_clusters=[0, 3, 1] output_clusters=[6, 3]>
        MODELS_INFO: [("eWeLink", "WB01")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                ],
            },
        }
    }

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON): {COMMAND: COMMAND_TOGGLE},
        (DOUBLE_PRESS, BUTTON): {COMMAND: COMMAND_ON},
        (LONG_PRESS, BUTTON): {COMMAND: COMMAND_OFF},
    }
