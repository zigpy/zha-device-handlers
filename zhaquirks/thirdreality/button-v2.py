"""Third Reality plug devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import  MultistateInput
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef
from zhaquirks.const import (
    COMMAND,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_RELEASE,
    COMMAND_SINGLE,
    DOUBLE_PRESS,
    LONG_PRESS,
    LONG_RELEASE,
    SHORT_PRESS,
    ZHA_SEND_EVENT,
    VALUE,
)

MOVEMENT_TYPE = {
    0: COMMAND_HOLD,
    1: COMMAND_SINGLE,
    2: COMMAND_DOUBLE,
    255: COMMAND_RELEASE,
}

class MultistateInputCluster(CustomCluster, MultistateInput):
    """Multistate input cluster."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self._current_state = {}
        super().__init__(*args, **kwargs)

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == 0x0055:
            self._current_state[0x0055] = action = MOVEMENT_TYPE.get(value)
            event_args = {VALUE: value}
            if action is not None:
                self.listener_event(ZHA_SEND_EVENT, action, event_args)

            # show something in the sensor in HA
            super()._update_attribute(0, action)


class ThirdRealityButtonCluster(CustomCluster):
    """Third Reality's button private cluster."""

    cluster_id = 0xFF01

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        # cancel double click
        cancel_bouble_click: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )



(
    QuirkBuilder("Third Reality, Inc", "3RSB22BZ")
    .replaces(ThirdRealityButtonCluster)
    .replaces(MultistateInputCluster)
    .number(
        attribute_name=ThirdRealityButtonCluster.AttributeDefs.cancel_bouble_click.name,
        cluster_id=ThirdRealityButtonCluster.cluster_id,
        endpoint_id=1,
        min_value=0,
        max_value=65535,
        step=1,
        translation_key="cancel_bouble_click",
        fallback_name="Cancel double click",
    )
    .device_automation_triggers(
        {
            (DOUBLE_PRESS, DOUBLE_PRESS): {COMMAND: COMMAND_DOUBLE},
            (SHORT_PRESS, SHORT_PRESS): {COMMAND: COMMAND_SINGLE},
            (LONG_PRESS, LONG_PRESS): {COMMAND: COMMAND_HOLD},
            (LONG_RELEASE, LONG_RELEASE): {COMMAND: COMMAND_RELEASE},
        }
    )
    .add_to_registry()
)
