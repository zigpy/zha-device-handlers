"""Echostar Sage Doorbell Sensor Device."""

from zigpy.profiles import zha
from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    CLUSTER_ID,
    COMMAND,
    COMMAND_OFF,
    COMMAND_ON,
    ENDPOINT_ID,
    SHORT_PRESS,
)

MANUFACTURER = " Echostar"
MODEL = "   Bell"


(
    QuirkBuilder(" Echostar", "   Bell")
    .replaces_endpoint(
        endpoint_id=18,
        profile_id=zha.PROFILE_ID,
        device_type=zha.DeviceType.ON_OFF_SWITCH,
    )
    .device_automation_triggers(
        {
            (SHORT_PRESS, BUTTON_1): {
                COMMAND: COMMAND_ON,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 18,
            },
            (SHORT_PRESS, BUTTON_2): {
                COMMAND: COMMAND_OFF,
                CLUSTER_ID: 6,
                ENDPOINT_ID: 18,
            },
        }
    )
    .add_to_registry()
)
