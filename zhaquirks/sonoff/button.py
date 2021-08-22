import logging

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    COMMAND,
    COMMAND_ON,
    COMMAND_TOGGLE,
    COMMAND_OFF,
    BUTTON,
    LONG_PRESS,
    SHORT_PRESS,
    DOUBLE_PRESS,
)
from zigpy.zcl.clusters.general import (
    Basic,
    PowerConfiguration,
    Identify,
    OnOff,
)

_LOGGER = logging.getLogger(__name__)

class SonoffButton(CustomDevice):
    """Custom device representing sonoff devices."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
    
    signature = {
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
        }
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
