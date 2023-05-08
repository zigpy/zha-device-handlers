import copy
import logging

from zigpy import types as t
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    Alarms,
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    OnOff,
    Ota,
    Scenes,
    Time,
)

from zhaquirks.const import (
    ALT_DOUBLE_PRESS,
    ALT_SHORT_PRESS,
    ARGS,
    ATTR_ID,
    BUTTON,
    CLUSTER_ID,
    COMMAND,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_OFF,
    COMMAND_SINGLE,
    COMMAND_TOGGLE,
    COMMAND_TRIPLE,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PRESS_TYPE,
    PROFILE_ID,
    SHORT_PRESS,
    TRIPLE_PRESS,
    VALUE,
    ZHA_SEND_EVENT,
)
from zhaquirks.xiaomi import (
    LUMI,
    DeviceTemperatureCluster,
    OnOffCluster,
    XiaomiCustomDevice,
    XiaomiMeteringCluster,
)
from zhaquirks.xiaomi.aqara.opple_remote import (
    PRESS_TYPES,
    MultistateInputCluster,
    OppleCluster,
)
from zhaquirks.xiaomi.aqara.opple_switch import OppleIndicatorLight, OppleOperationMode

_LOGGER = logging.getLogger(__name__)


class AqaraH1SwitchCluster(OppleCluster):
    """Xiaomi mfg cluster implementation."""

    attributes = copy.deepcopy(OppleCluster.attributes)

    attributes.update(
        {
            0x0002: ("power_outage_count", t.uint8_t, True),
            0x000A: ("switch_type", t.uint8_t, True),  # values can be: 1 or 2
            0x00F0: ("reverse_indicator_light", OppleIndicatorLight, True),
            0x0125: ("switch_mode", t.uint8_t, True),  # values can be: 1 or 2
            0x0200: ("operation_mode", OppleOperationMode, True),
            0x0201: ("power_outage_memory", t.Bool, True),
            0x0202: ("auto_off", t.Bool, True),
            0x0203: ("do_not_disturb", t.Bool, True),
        }
    )

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == 0x00FC:
            self._current_state = PRESS_TYPES.get(value)
            event_args = {
                PRESS_TYPE: self._current_state,
                ATTR_ID: attrid,
                VALUE: value,
            }
            self.listener_event(ZHA_SEND_EVENT, self._current_state, event_args)
            # show something in the sensor in HA
            super()._update_attribute(0, self._current_state)


class AqaraH1SingleRockerSwitch(XiaomiCustomDevice):
    """Aqara H1 Single Rocker Switch (with neutral)."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.switch.n1aeu1")],
        ENDPOINTS: {
            #  input_clusters=[0, 2, 3, 4, 5, 6, 18, 64704], output_clusters=[10, 25]
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    DeviceTemperatureCluster.cluster_id,  # 2
                    Identify.cluster_id,  # 3
                    Groups.cluster_id,  # 4
                    Scenes.cluster_id,  # 5
                    OnOff.cluster_id,  # 6
                    Alarms.cluster_id,  # 9
                    XiaomiMeteringCluster.cluster_id,  # 0x0702
                    0x0B04,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,  # 0x000a
                    Ota.cluster_id,  # 0x0019
                ],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,  # 0x0021
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    Identify.cluster_id,  # 3
                    Groups.cluster_id,  # 4
                    Scenes.cluster_id,  # 5
                    OnOffCluster,  # 6
                    Alarms.cluster_id,  # 9
                    XiaomiMeteringCluster.cluster_id,  # 0x0702
                    AqaraH1SwitchCluster,  # 0xFCC0 / 64704
                    0x0B04,
                ],
                OUTPUT_CLUSTERS: [
                    MultistateInputCluster,  # 18
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON): {
            ENDPOINT_ID: 1,
            CLUSTER_ID: 0,
            COMMAND: COMMAND_SINGLE,
            ARGS: {ATTR_ID: 0x00F9},
        },
        (DOUBLE_PRESS, BUTTON): {
            ENDPOINT_ID: 1,
            CLUSTER_ID: 0,
            COMMAND: COMMAND_DOUBLE,
            ARGS: {ATTR_ID: 0x00FA},
        },
        (TRIPLE_PRESS, BUTTON): {
            ENDPOINT_ID: 1,
            CLUSTER_ID: 0,
            COMMAND: COMMAND_TRIPLE,
            ARGS: {ATTR_ID: 0x00FB},
        },
        (LONG_PRESS, BUTTON): {
            CLUSTER_ID: AqaraH1SwitchCluster.cluster_id,
            COMMAND: COMMAND_HOLD,
        },
        (ALT_SHORT_PRESS, BUTTON): {COMMAND: COMMAND_TOGGLE, ENDPOINT_ID: 1, ARGS: []},
        (ALT_DOUBLE_PRESS, BUTTON): {COMMAND: COMMAND_OFF, ENDPOINT_ID: 1, ARGS: []},
    }
    # {
    #     # triggers when operation_mode == event
    #     # the button doesn't send an release event after hold
    #     (SHORT_PRESS, BUTTON): {COMMAND: COMMAND_SINGLE},
    #     (DOUBLE_PRESS, BUTTON): {COMMAND: COMMAND_DOUBLE},
    #     (TRIPLE_PRESS, BUTTON): {COMMAND: COMMAND_TRIPLE},
    #     (LONG_PRESS, BUTTON): {COMMAND: COMMAND_1_HOLD},
    #     # triggers when operation_mode == command
    #     (ALT_SHORT_PRESS, BUTTON): {COMMAND: COMMAND_TOGGLE, ENDPOINT_ID: 1, ARGS: []},
    #     (ALT_DOUBLE_PRESS, BUTTON): {COMMAND: COMMAND_OFF, ENDPOINT_ID: 1, ARGS: []},
    #     (COMMAND_BUTTON_SINGLE, BUTTON_1): {
    #         ENDPOINT_ID: 1,
    #         CLUSTER_ID: 18,
    #         ARGS: {ATTR_ID: 0x0055, PRESS_TYPE: COMMAND_SINGLE, VALUE: 1},
    #     },
    #     (COMMAND_BUTTON_DOUBLE, BUTTON_1): {
    #         ENDPOINT_ID: 1,
    #         CLUSTER_ID: 18,
    #         ARGS: {ATTR_ID: 0x0055, PRESS_TYPE: COMMAND_DOUBLE, VALUE: 2},
    #     },
    #     (COMMAND_BUTTON_HOLD, BUTTON): {
    #         ENDPOINT_ID: 1,
    #         CLUSTER_ID: 0xFCC0,
    #         # COMMAND: COMMAND_ATTRIBUTE_UPDATED,
    #         ARGS: {ATTR_ID: 0x00FC, VALUE: False},
    #     },
    # }
