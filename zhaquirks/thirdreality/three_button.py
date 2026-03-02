"""Third Reality button devices."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import MultistateInput

from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    COMMAND,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_RELEASE,
    COMMAND_SINGLE,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    LONG_PRESS,
    LONG_RELEASE,
    SHORT_PRESS,
    VALUE,
    ZHA_SEND_EVENT,
)

PRESS_TYPE = {
    0: COMMAND_HOLD,
    1: COMMAND_SINGLE,
    2: COMMAND_DOUBLE,
    255: COMMAND_RELEASE,
}


class MultistateInputCluster(CustomCluster, MultistateInput):
    """Multistate input cluster."""

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == 0x0055 and (action := PRESS_TYPE.get(value)) is not None:
            self.listener_event(ZHA_SEND_EVENT, action, {VALUE: value})


(
    QuirkBuilder("Third Reality, Inc", "3RSB01085Z")
    .replaces(MultistateInputCluster)
    .replaces(MultistateInputCluster, endpoint_id=2)
    .replaces(MultistateInputCluster, endpoint_id=3)
    .device_automation_triggers(
        {
            (DOUBLE_PRESS, BUTTON_1): {COMMAND: COMMAND_DOUBLE, ENDPOINT_ID: 1},
            (SHORT_PRESS, BUTTON_1): {COMMAND: COMMAND_SINGLE, ENDPOINT_ID: 1},
            (LONG_PRESS, BUTTON_1): {COMMAND: COMMAND_HOLD, ENDPOINT_ID: 1},
            (LONG_RELEASE, BUTTON_1): {COMMAND: COMMAND_RELEASE, ENDPOINT_ID: 1},
            (DOUBLE_PRESS, BUTTON_2): {COMMAND: COMMAND_DOUBLE, ENDPOINT_ID: 2},
            (SHORT_PRESS, BUTTON_2): {COMMAND: COMMAND_SINGLE, ENDPOINT_ID: 2},
            (LONG_PRESS, BUTTON_2): {COMMAND: COMMAND_HOLD, ENDPOINT_ID: 2},
            (LONG_RELEASE, BUTTON_2): {COMMAND: COMMAND_RELEASE, ENDPOINT_ID: 2},
            (DOUBLE_PRESS, BUTTON_3): {COMMAND: COMMAND_DOUBLE, ENDPOINT_ID: 3},
            (SHORT_PRESS, BUTTON_3): {COMMAND: COMMAND_SINGLE, ENDPOINT_ID: 3},
            (LONG_PRESS, BUTTON_3): {COMMAND: COMMAND_HOLD, ENDPOINT_ID: 3},
            (LONG_RELEASE, BUTTON_3): {COMMAND: COMMAND_RELEASE, ENDPOINT_ID: 3},
        }
    )
    .add_to_registry()
)
