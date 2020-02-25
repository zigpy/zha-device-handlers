"""Xiaomi aqara button sensor."""
import logging

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Basic, Identify, MultistateInput, OnOff

from .. import LUMI, BasicCluster, PowerConfigurationCluster, XiaomiCustomDevice
from ... import CustomCluster
from ...const import (
    COMMAND,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_RELEASE,
    COMMAND_SHAKE,
    COMMAND_SINGLE,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    LONG_RELEASE,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHAKEN,
    SHORT_PRESS,
    SKIP_CONFIGURATION,
    VALUE,
    ZHA_SEND_EVENT,
)

B1ACN01_HOLD = 0
B1ACN01_RELEASE = 255
BUTTON_DEVICE_TYPE = 0x5F01
BUTTON_DEVICE_TYPEB = 259
DOUBLE = 2
HOLD = 16
RELEASE = 17
SHAKE = 18
SINGLE = 1
STATUS_TYPE_ATTR = 0x0055  # decimal = 85

MOVEMENT_TYPE = {
    B1ACN01_HOLD: COMMAND_HOLD,
    SINGLE: COMMAND_SINGLE,
    DOUBLE: COMMAND_DOUBLE,
    HOLD: COMMAND_HOLD,
    RELEASE: COMMAND_RELEASE,
    B1ACN01_RELEASE: COMMAND_RELEASE,
    SHAKE: COMMAND_SHAKE,
}

_LOGGER = logging.getLogger(__name__)


class MultistateInputCluster(CustomCluster, MultistateInput):
    """Multistate input cluster."""

    cluster_id = MultistateInput.cluster_id

    def __init__(self, *args, **kwargs):
        """Init."""
        self._current_state = {}
        super().__init__(*args, **kwargs)

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == STATUS_TYPE_ATTR:
            self._current_state[STATUS_TYPE_ATTR] = action = MOVEMENT_TYPE.get(value)
            event_args = {VALUE: value}
            if action is not None:
                self.listener_event(ZHA_SEND_EVENT, action, event_args)

            # show something in the sensor in HA
            super()._update_attribute(0, action)


class SwitchAQ3(XiaomiCustomDevice):
    """Aqara button device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=24321
        # device_version=1
        # input_clusters=[0, 18, 6, 1]
        # output_clusters=[0]>
        MODELS_INFO: [(LUMI, "lumi.sensor_switch.aq3")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: BUTTON_DEVICE_TYPE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                    OnOff.cluster_id,
                    MultistateInput.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Basic.cluster_id],
            }
        },
    }
    replacement = {
        SKIP_CONFIGURATION: True,
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    PowerConfigurationCluster,
                    MultistateInputCluster,
                ],
                OUTPUT_CLUSTERS: [Basic.cluster_id, OnOff.cluster_id],
            }
        },
    }

    device_automation_triggers = {
        (SHAKEN, SHAKEN): {COMMAND: COMMAND_SHAKE},
        (DOUBLE_PRESS, DOUBLE_PRESS): {COMMAND: COMMAND_DOUBLE},
        (SHORT_PRESS, SHORT_PRESS): {COMMAND: COMMAND_SINGLE},
        (LONG_PRESS, LONG_PRESS): {COMMAND: COMMAND_HOLD},
        (LONG_RELEASE, LONG_RELEASE): {COMMAND: COMMAND_HOLD},
    }


class SwitchAQ3B(XiaomiCustomDevice):
    """Aqara button device - alternate version."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=259
        # device_version=1
        # input_clusters=[0, 18, 3]
        # output_clusters=[0]>
        MODELS_INFO: [(LUMI, "lumi.remote.b1acn01")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: BUTTON_DEVICE_TYPEB,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    MultistateInput.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Basic.cluster_id],
            }
        },
    }
    replacement = {
        SKIP_CONFIGURATION: True,
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    PowerConfigurationCluster,
                    MultistateInputCluster,
                ],
                OUTPUT_CLUSTERS: [Basic.cluster_id],
            }
        },
    }

    device_automation_triggers = SwitchAQ3.device_automation_triggers
