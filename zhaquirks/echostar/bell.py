"""Echostar Sage Doorbell Sensor Device."""

from zigpy.profiles import zha
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import OnOff

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

(
    QuirkBuilder(" Echostar", "   Bell")
    .replaces_endpoint(
        18,
        device_type=zha.DeviceType.ON_OFF_SWITCH,
    )
    .device_automation_triggers(
        {
            (SHORT_PRESS, BUTTON_1): {
                COMMAND: COMMAND_ON,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: 18,
            },
            (SHORT_PRESS, BUTTON_2): {
                COMMAND: COMMAND_OFF,
                CLUSTER_ID: OnOff.cluster_id,
                ENDPOINT_ID: 18,
            },
        }
    )
    .add_to_registry()
)
