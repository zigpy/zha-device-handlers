"""Third Reality button devices."""

from typing import Final

import zigpy.types as t
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import MultistateInput
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import ButtonEvent, ButtonEventType, QuirkBuilder
from zhaquirks.clusters import CustomCluster
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


class ThirdRealityButtonCluster(CustomCluster):
    """Third Reality's button private cluster."""

    cluster_id = 0xFF01

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        disable_double_click: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder("Third Reality, Inc", "3RSB22BZ")
    .replaces(ThirdRealityButtonCluster)
    .replaces(MultistateInputCluster)
    .switch(
        attribute_name=ThirdRealityButtonCluster.AttributeDefs.disable_double_click.name,
        cluster_id=ThirdRealityButtonCluster.cluster_id,
        translation_key="disable_double_click",
        fallback_name="Disable double click",
    )
    .device_automation_triggers(
        {
            (DOUBLE_PRESS, DOUBLE_PRESS): {COMMAND: COMMAND_DOUBLE},
            (SHORT_PRESS, SHORT_PRESS): {COMMAND: COMMAND_SINGLE},
            (LONG_PRESS, LONG_PRESS): {COMMAND: COMMAND_HOLD},
            (LONG_RELEASE, LONG_RELEASE): {COMMAND: COMMAND_RELEASE},
        }
    )
    # The button counts its presses, so its single press is a resolved gesture. It
    # reports the hold at the threshold. Its release is only taken as the end of
    # a hold seen, in case it also follows other presses.
    .button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.SINGLE_PRESS,
                trigger=(SHORT_PRESS, SHORT_PRESS),
            ),
            ButtonEvent(
                event_type=ButtonEventType.MULTI_PRESS,
                trigger=(DOUBLE_PRESS, DOUBLE_PRESS),
                press_count=2,
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_START,
                trigger=(LONG_PRESS, LONG_PRESS),
            ),
            ButtonEvent(
                event_type=ButtonEventType.LONG_PRESS_END,
                trigger=(LONG_RELEASE, LONG_RELEASE),
                while_held=True,
            ),
        ],
        cluster_id=MultistateInputCluster.cluster_id,
        cluster_type=ClusterType.Server,
        unique_id_suffix="button",
        translation_key="button",
        fallback_name="Button",
    )
    .add_to_registry()
)
