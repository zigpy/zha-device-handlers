"""Xiaomi aqara opple remote devices."""

from typing import Final

from zigpy import types
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import MultistateInput
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks import CustomCluster
from zhaquirks.builder import QuirkBuilder
from zhaquirks.const import (
    ALT_DOUBLE_PRESS,
    ALT_LONG_PRESS,
    ALT_SHORT_PRESS,
    ATTR_ID,
    BUTTON,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    BUTTON_5,
    BUTTON_6,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_MOVE_COLOR_TEMP,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STEP,
    COMMAND_STEP_COLOR_TEMP,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    LONG_PRESS,
    LONG_RELEASE,
    PARAMS,
    PRESS_TYPE,
    SHORT_PRESS,
    TRIPLE_PRESS,
    VALUE,
    ZHA_SEND_EVENT,
)
from zhaquirks.xiaomi import (
    LUMI,
    BasicCluster,
    XiaomiAqaraE1Cluster,
    XiaomiCustomZigpyDevice,
    XiaomiPowerConfiguration,
)

PRESS_TYPES = {0: "hold", 1: "single", 2: "double", 3: "triple", 255: "release"}
STATUS_TYPE_ATTR = 0x0055  # decimal = 85

COMMAND_1_SINGLE = "1_single"
COMMAND_1_DOUBLE = "1_double"
COMMAND_1_TRIPLE = "1_triple"
COMMAND_1_HOLD = "1_hold"
COMMAND_1_RELEASE = "1_release"

COMMAND_2_SINGLE = "2_single"
COMMAND_2_DOUBLE = "2_double"
COMMAND_2_TRIPLE = "2_triple"
COMMAND_2_HOLD = "2_hold"
COMMAND_2_RELEASE = "2_release"

COMMAND_3_SINGLE = "3_single"
COMMAND_3_DOUBLE = "3_double"
COMMAND_3_TRIPLE = "3_triple"
COMMAND_3_HOLD = "3_hold"
COMMAND_3_RELEASE = "3_release"

COMMAND_4_SINGLE = "4_single"
COMMAND_4_DOUBLE = "4_double"
COMMAND_4_TRIPLE = "4_triple"
COMMAND_4_HOLD = "4_hold"
COMMAND_4_RELEASE = "4_release"

COMMAND_5_SINGLE = "5_single"
COMMAND_5_DOUBLE = "5_double"
COMMAND_5_TRIPLE = "5_triple"
COMMAND_5_HOLD = "5_hold"
COMMAND_5_RELEASE = "5_release"

COMMAND_6_SINGLE = "6_single"
COMMAND_6_DOUBLE = "6_double"
COMMAND_6_TRIPLE = "6_triple"
COMMAND_6_HOLD = "6_hold"
COMMAND_6_RELEASE = "6_release"

OPPLE_MFG_CODE = 0x115F


class MultistateInputCluster(CustomCluster, MultistateInput):
    """Multistate input cluster."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self._current_state = None
        super().__init__(*args, **kwargs)

    async def configure_reporting(
        self,
        attribute,
        min_interval,
        max_interval,
        reportable_change,
        manufacturer=None,
    ):
        """Configure reporting."""

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == STATUS_TYPE_ATTR:
            self._current_state = PRESS_TYPES.get(value)
            event_args = {
                BUTTON: self.endpoint.endpoint_id,
                PRESS_TYPE: self._current_state,
                ATTR_ID: attrid,
                VALUE: value,
            }
            action = f"{self.endpoint.endpoint_id}_{self._current_state}"
            self.listener_event(ZHA_SEND_EVENT, action, event_args)
            # show something in the sensor in HA
            super()._update_attribute(0, action)


class OppleCluster(XiaomiAqaraE1Cluster):
    """Opple cluster."""

    class AttributeDefs(XiaomiAqaraE1Cluster.AttributeDefs):
        """Attribute definitions."""

        mode: Final = ZCLAttributeDef(
            id=0x0009, type=types.uint8_t, manufacturer_code=OPPLE_MFG_CODE
        )


B286_TRIGGERS = {
    (DOUBLE_PRESS, BUTTON_1): {
        COMMAND: COMMAND_STEP,
        ENDPOINT_ID: 1,
        PARAMS: {"step_mode": 1},
    },
    (SHORT_PRESS, BUTTON_1): {COMMAND: COMMAND_OFF, ENDPOINT_ID: 1},
    (LONG_PRESS, BUTTON_1): {
        COMMAND: COMMAND_STEP_COLOR_TEMP,
        ENDPOINT_ID: 1,
        PARAMS: {"step_mode": 1},
    },
    (DOUBLE_PRESS, BUTTON_2): {
        COMMAND: COMMAND_STEP,
        ENDPOINT_ID: 1,
        PARAMS: {"step_mode": 0},
    },
    (SHORT_PRESS, BUTTON_2): {COMMAND: COMMAND_ON, ENDPOINT_ID: 1},
    (LONG_PRESS, BUTTON_2): {
        COMMAND: COMMAND_STEP_COLOR_TEMP,
        ENDPOINT_ID: 1,
        PARAMS: {"step_mode": 3},
    },
    (ALT_SHORT_PRESS, BUTTON_1): {COMMAND: COMMAND_1_SINGLE},
    (ALT_DOUBLE_PRESS, BUTTON_1): {COMMAND: COMMAND_1_DOUBLE},
    (TRIPLE_PRESS, BUTTON_1): {COMMAND: COMMAND_1_TRIPLE},
    (ALT_LONG_PRESS, BUTTON_1): {COMMAND: COMMAND_1_HOLD},
    (LONG_RELEASE, BUTTON_1): {COMMAND: COMMAND_1_RELEASE},
    (ALT_SHORT_PRESS, BUTTON_2): {COMMAND: COMMAND_2_SINGLE},
    (ALT_DOUBLE_PRESS, BUTTON_2): {COMMAND: COMMAND_2_DOUBLE},
    (TRIPLE_PRESS, BUTTON_2): {COMMAND: COMMAND_2_TRIPLE},
    (ALT_LONG_PRESS, BUTTON_2): {COMMAND: COMMAND_2_HOLD},
    (LONG_RELEASE, BUTTON_2): {COMMAND: COMMAND_2_RELEASE},
}

B486_TRIGGERS = {
    (SHORT_PRESS, BUTTON_1): {COMMAND: COMMAND_OFF, ENDPOINT_ID: 1},
    (SHORT_PRESS, BUTTON_2): {COMMAND: COMMAND_ON, ENDPOINT_ID: 1},
    (SHORT_PRESS, BUTTON_3): {
        COMMAND: COMMAND_STEP,
        ENDPOINT_ID: 1,
        PARAMS: {"step_mode": 1},
    },
    (DOUBLE_PRESS, BUTTON_3): {
        COMMAND: COMMAND_STEP_COLOR_TEMP,
        ENDPOINT_ID: 1,
        PARAMS: {"step_mode": 1},
    },
    (SHORT_PRESS, BUTTON_4): {
        COMMAND: COMMAND_STEP,
        ENDPOINT_ID: 1,
        PARAMS: {"step_mode": 0},
    },
    (DOUBLE_PRESS, BUTTON_4): {
        COMMAND: COMMAND_STEP_COLOR_TEMP,
        ENDPOINT_ID: 1,
        PARAMS: {"step_mode": 3},
    },
    (ALT_SHORT_PRESS, BUTTON_1): {COMMAND: COMMAND_1_SINGLE},
    (ALT_DOUBLE_PRESS, BUTTON_1): {COMMAND: COMMAND_1_DOUBLE},
    (TRIPLE_PRESS, BUTTON_1): {COMMAND: COMMAND_1_TRIPLE},
    (ALT_LONG_PRESS, BUTTON_1): {COMMAND: COMMAND_1_HOLD},
    (LONG_RELEASE, BUTTON_1): {COMMAND: COMMAND_1_RELEASE},
    (ALT_SHORT_PRESS, BUTTON_2): {COMMAND: COMMAND_2_SINGLE},
    (ALT_DOUBLE_PRESS, BUTTON_2): {COMMAND: COMMAND_2_DOUBLE},
    (TRIPLE_PRESS, BUTTON_2): {COMMAND: COMMAND_2_TRIPLE},
    (ALT_LONG_PRESS, BUTTON_2): {COMMAND: COMMAND_2_HOLD},
    (LONG_RELEASE, BUTTON_2): {COMMAND: COMMAND_2_RELEASE},
    (ALT_SHORT_PRESS, BUTTON_3): {COMMAND: COMMAND_3_SINGLE},
    (ALT_DOUBLE_PRESS, BUTTON_3): {COMMAND: COMMAND_3_DOUBLE},
    (TRIPLE_PRESS, BUTTON_3): {COMMAND: COMMAND_3_TRIPLE},
    (ALT_LONG_PRESS, BUTTON_3): {COMMAND: COMMAND_3_HOLD},
    (LONG_RELEASE, BUTTON_3): {COMMAND: COMMAND_3_RELEASE},
    (ALT_SHORT_PRESS, BUTTON_4): {COMMAND: COMMAND_4_SINGLE},
    (ALT_DOUBLE_PRESS, BUTTON_4): {COMMAND: COMMAND_4_DOUBLE},
    (TRIPLE_PRESS, BUTTON_4): {COMMAND: COMMAND_4_TRIPLE},
    (ALT_LONG_PRESS, BUTTON_4): {COMMAND: COMMAND_4_HOLD},
    (LONG_RELEASE, BUTTON_4): {COMMAND: COMMAND_4_RELEASE},
}

B686_TRIGGERS = {
    (SHORT_PRESS, BUTTON_1): {COMMAND: COMMAND_OFF, ENDPOINT_ID: 1},
    (SHORT_PRESS, BUTTON_2): {COMMAND: COMMAND_ON, ENDPOINT_ID: 1},
    (SHORT_PRESS, BUTTON_3): {
        COMMAND: COMMAND_STEP,
        ENDPOINT_ID: 1,
        PARAMS: {"step_mode": 1},
    },
    (LONG_PRESS, BUTTON_3): {
        COMMAND: COMMAND_MOVE,
        ENDPOINT_ID: 1,
        PARAMS: {"move_mode": 1},
    },
    (SHORT_PRESS, BUTTON_4): {
        COMMAND: COMMAND_STEP,
        ENDPOINT_ID: 1,
        PARAMS: {"step_mode": 0},
    },
    (LONG_PRESS, BUTTON_4): {
        COMMAND: COMMAND_MOVE,
        ENDPOINT_ID: 1,
        PARAMS: {"move_mode": 0},
    },
    (SHORT_PRESS, BUTTON_5): {
        COMMAND: COMMAND_STEP_COLOR_TEMP,
        ENDPOINT_ID: 1,
        PARAMS: {"step_mode": 1},
    },
    (LONG_PRESS, BUTTON_5): {
        COMMAND: COMMAND_MOVE_COLOR_TEMP,
        ENDPOINT_ID: 1,
        PARAMS: {"move_mode": 1},
    },
    (SHORT_PRESS, BUTTON_6): {
        COMMAND: COMMAND_STEP_COLOR_TEMP,
        ENDPOINT_ID: 1,
        PARAMS: {"step_mode": 3},
    },
    (LONG_PRESS, BUTTON_6): {
        COMMAND: COMMAND_MOVE_COLOR_TEMP,
        ENDPOINT_ID: 1,
        PARAMS: {"move_mode": 3},
    },
    (ALT_SHORT_PRESS, BUTTON_1): {COMMAND: COMMAND_1_SINGLE},
    (ALT_DOUBLE_PRESS, BUTTON_1): {COMMAND: COMMAND_1_DOUBLE},
    (TRIPLE_PRESS, BUTTON_1): {COMMAND: COMMAND_1_TRIPLE},
    (ALT_LONG_PRESS, BUTTON_1): {COMMAND: COMMAND_1_HOLD},
    (LONG_RELEASE, BUTTON_1): {COMMAND: COMMAND_1_RELEASE},
    (ALT_SHORT_PRESS, BUTTON_2): {COMMAND: COMMAND_2_SINGLE},
    (ALT_DOUBLE_PRESS, BUTTON_2): {COMMAND: COMMAND_2_DOUBLE},
    (TRIPLE_PRESS, BUTTON_2): {COMMAND: COMMAND_2_TRIPLE},
    (ALT_LONG_PRESS, BUTTON_2): {COMMAND: COMMAND_2_HOLD},
    (LONG_RELEASE, BUTTON_2): {COMMAND: COMMAND_2_RELEASE},
    (ALT_SHORT_PRESS, BUTTON_3): {COMMAND: COMMAND_3_SINGLE},
    (ALT_DOUBLE_PRESS, BUTTON_3): {COMMAND: COMMAND_3_DOUBLE},
    (TRIPLE_PRESS, BUTTON_3): {COMMAND: COMMAND_3_TRIPLE},
    (ALT_LONG_PRESS, BUTTON_3): {COMMAND: COMMAND_3_HOLD},
    (LONG_RELEASE, BUTTON_3): {COMMAND: COMMAND_3_RELEASE},
    (ALT_SHORT_PRESS, BUTTON_4): {COMMAND: COMMAND_4_SINGLE},
    (ALT_DOUBLE_PRESS, BUTTON_4): {COMMAND: COMMAND_4_DOUBLE},
    (TRIPLE_PRESS, BUTTON_4): {COMMAND: COMMAND_4_TRIPLE},
    (ALT_LONG_PRESS, BUTTON_4): {COMMAND: COMMAND_4_HOLD},
    (LONG_RELEASE, BUTTON_4): {COMMAND: COMMAND_4_RELEASE},
    (ALT_SHORT_PRESS, BUTTON_5): {COMMAND: COMMAND_5_SINGLE},
    (ALT_DOUBLE_PRESS, BUTTON_5): {COMMAND: COMMAND_5_DOUBLE},
    (TRIPLE_PRESS, BUTTON_5): {COMMAND: COMMAND_5_TRIPLE},
    (ALT_LONG_PRESS, BUTTON_5): {COMMAND: COMMAND_5_HOLD},
    (LONG_RELEASE, BUTTON_5): {COMMAND: COMMAND_5_RELEASE},
    (ALT_SHORT_PRESS, BUTTON_6): {COMMAND: COMMAND_6_SINGLE},
    (ALT_DOUBLE_PRESS, BUTTON_6): {COMMAND: COMMAND_6_DOUBLE},
    (TRIPLE_PRESS, BUTTON_6): {COMMAND: COMMAND_6_TRIPLE},
    (ALT_LONG_PRESS, BUTTON_6): {COMMAND: COMMAND_6_HOLD},
    (LONG_RELEASE, BUTTON_6): {COMMAND: COMMAND_6_RELEASE},
}


# Each button reports its presses on its own endpoint. Firmwares expose
# different endpoint counts; `adds` skips any endpoint that isn't present.
(
    QuirkBuilder(LUMI, "lumi.remote.b286opcn01")
    .zigpy_device_class(XiaomiCustomZigpyDevice)
    .replaces(BasicCluster, endpoint_id=1)
    .replaces(XiaomiPowerConfiguration, endpoint_id=1)
    .adds(OppleCluster, endpoint_id=1)
    .writes_attributes(
        endpoint_id=1,
        cluster_id=OppleCluster.cluster_id,
        attributes={OppleCluster.AttributeDefs.mode: 0x01},
    )
    .adds_endpoint(endpoint_id=2, device_type=zha.DeviceType.ON_OFF_LIGHT_SWITCH)
    .adds(MultistateInputCluster, endpoint_id=1)
    .adds(MultistateInputCluster, endpoint_id=2)
    .device_automation_triggers(B286_TRIGGERS)
    .add_to_registry()
)

(
    QuirkBuilder(LUMI, "lumi.remote.b486opcn01")
    .zigpy_device_class(XiaomiCustomZigpyDevice)
    .replaces(BasicCluster, endpoint_id=1)
    .replaces(XiaomiPowerConfiguration, endpoint_id=1)
    .adds(OppleCluster, endpoint_id=1)
    .writes_attributes(
        endpoint_id=1,
        cluster_id=OppleCluster.cluster_id,
        attributes={OppleCluster.AttributeDefs.mode: 0x01},
    )
    .adds_endpoint(endpoint_id=2, device_type=zha.DeviceType.ON_OFF_LIGHT_SWITCH)
    .adds_endpoint(endpoint_id=3, device_type=zha.DeviceType.ON_OFF_LIGHT_SWITCH)
    .adds_endpoint(endpoint_id=4, device_type=zha.DeviceType.ON_OFF_LIGHT_SWITCH)
    .adds(MultistateInputCluster, endpoint_id=1)
    .adds(MultistateInputCluster, endpoint_id=2)
    .adds(MultistateInputCluster, endpoint_id=3)
    .adds(MultistateInputCluster, endpoint_id=4)
    .device_automation_triggers(B486_TRIGGERS)
    .add_to_registry()
)

(
    QuirkBuilder(LUMI, "lumi.remote.b686opcn01")
    .zigpy_device_class(XiaomiCustomZigpyDevice)
    .replaces(BasicCluster, endpoint_id=1)
    .replaces(XiaomiPowerConfiguration, endpoint_id=1)
    .adds(OppleCluster, endpoint_id=1)
    .writes_attributes(
        endpoint_id=1,
        cluster_id=OppleCluster.cluster_id,
        attributes={OppleCluster.AttributeDefs.mode: 0x01},
    )
    .adds_endpoint(endpoint_id=2, device_type=zha.DeviceType.ON_OFF_LIGHT_SWITCH)
    .adds_endpoint(endpoint_id=3, device_type=zha.DeviceType.ON_OFF_LIGHT_SWITCH)
    .adds_endpoint(endpoint_id=4, device_type=zha.DeviceType.ON_OFF_LIGHT_SWITCH)
    .adds_endpoint(endpoint_id=5, device_type=zha.DeviceType.ON_OFF_LIGHT_SWITCH)
    .adds_endpoint(endpoint_id=6, device_type=zha.DeviceType.ON_OFF_LIGHT_SWITCH)
    .adds(MultistateInputCluster, endpoint_id=1)
    .adds(MultistateInputCluster, endpoint_id=2)
    .adds(MultistateInputCluster, endpoint_id=3)
    .adds(MultistateInputCluster, endpoint_id=4)
    .adds(MultistateInputCluster, endpoint_id=5)
    .adds(MultistateInputCluster, endpoint_id=6)
    .device_automation_triggers(B686_TRIGGERS)
    .add_to_registry()
)
