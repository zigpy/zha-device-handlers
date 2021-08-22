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
    LONG_PRESS,
    SHORT_PRESS,
    DOUBLE_PRESS,
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
                    0x0000,
                    0x0001,
                    0x0003,
                ],
                OUTPUT_CLUSTERS: [
                    0x0003,
                    0x0006
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
                    0x0000,
                    0x0001,
                    0x0003,
                ],
                OUTPUT_CLUSTERS: [
                    0x0003,
                    0x0006
                ],
            },  
        }
    }

    device_automation_triggers = {
        (SHORT_PRESS): {COMMAND: COMMAND_TOGGLE},
        (DOUBLE_PRESS): {COMMAND: COMMAND_ON},
        (LONG_PRESS): {COMMAND: COMMAND_OFF},
    }
