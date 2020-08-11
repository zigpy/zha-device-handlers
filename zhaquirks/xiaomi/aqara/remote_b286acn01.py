"""Xiaomi aqara double key switch device."""
import logging

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    AnalogInput,
    Basic,
    Groups,
    Identify,
    MultistateInput,
    OnOff,
    Ota,
    Scenes,
)

from .. import LUMI, BasicCluster, PowerConfigurationCluster, XiaomiCustomDevice
from ... import CustomCluster
from ...const import (
    ATTR_ID,
    BUTTON,
    BUTTON_1,
    BUTTON_2,
    COMMAND,
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
    SKIP_CONFIGURATION,
    VALUE,
    ZHA_SEND_EVENT,
)

BOTH_BUTTONS = "both_buttons"
BOTH_DOUBLE = "both_double"
BOTH_HOLD = "both_long press"
BOTH_SINGLE = "both_single"
ENDPOINT_MAP = {1: "left", 2: "right", 3: "both"}
LEFT_DOUBLE = "left_double"
LEFT_HOLD = "left_long press"
LEFT_SINGLE = "left_single"
PRESS_TYPES = {0: "long press", 1: "single", 2: "double"}
RIGHT_DOUBLE = "right_double"
RIGHT_HOLD = "right_long press"
RIGHT_SINGLE = "right_single"
STATUS_TYPE_ATTR = 0x0055  # decimal = 85
XIAOMI_CLUSTER_ID = 0xFFFF
XIAOMI_DEVICE_TYPE = 0x5F01
XIAOMI_DEVICE_TYPE2 = 0x5F02
XIAOMI_DEVICE_TYPE3 = 0x5F03

_LOGGER = logging.getLogger(__name__)


class RemoteB286ACN01(XiaomiCustomDevice):
    """Aqara double key switch device."""

    class MultistateInputCluster(CustomCluster, MultistateInput):
        """Multistate input cluster."""

        cluster_id = MultistateInput.cluster_id

        def __init__(self, *args, **kwargs):
            """Init."""
            self._current_state = None
            super().__init__(*args, **kwargs)

        def _update_attribute(self, attrid, value):
            super()._update_attribute(attrid, value)
            if attrid == STATUS_TYPE_ATTR:
                self._current_state = PRESS_TYPES.get(value)
                button = ENDPOINT_MAP.get(self.endpoint.endpoint_id)
                event_args = {
                    BUTTON: button,
                    PRESS_TYPE: self._current_state,
                    ATTR_ID: attrid,
                    VALUE: value,
                }
                action = "{}_{}".format(button, self._current_state)
                self.listener_event(ZHA_SEND_EVENT, action, event_args)
                # show something in the sensor in HA
                super()._update_attribute(0, action)

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=24321
        # device_version=1
        # input_clusters=[0, 3, 25, 65535, 18]
        # output_clusters=[0, 4, 3, 5, 25, 65535, 18]>
        MODELS_INFO: [
            (LUMI, "lumi.remote.b286acn01"),
            (LUMI, "lumi.remote.b286acn02"),
            (LUMI, "lumi.sensor_86sw2"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: XIAOMI_DEVICE_TYPE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Ota.cluster_id,
                    XIAOMI_CLUSTER_ID,
                    MultistateInputCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Ota.cluster_id,
                    XIAOMI_CLUSTER_ID,
                    MultistateInputCluster.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=24322
            # device_version=1
            # input_clusters=[3, 18]
            # output_clusters=[4, 3, 5, 18]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: XIAOMI_DEVICE_TYPE2,
                INPUT_CLUSTERS: [
                    Identify.cluster_id,
                    MultistateInputCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MultistateInputCluster.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=3 profile=260 device_type=24323
            # device_version=1
            # input_clusters=[3, 12]
            # output_clusters=[4, 3, 5, 12]>
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: XIAOMI_DEVICE_TYPE3,
                INPUT_CLUSTERS: [Identify.cluster_id, AnalogInput.cluster_id],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    AnalogInput.cluster_id,
                ],
            },
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
                    Identify.cluster_id,
                    Ota.cluster_id,
                    XIAOMI_CLUSTER_ID,
                    MultistateInputCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Ota.cluster_id,
                    XIAOMI_CLUSTER_ID,
                    MultistateInputCluster,
                    OnOff.cluster_id,
                ],
            },
            2: {
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [Identify.cluster_id, MultistateInputCluster],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MultistateInputCluster,
                    OnOff.cluster_id,
                ],
            },
            3: {
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [Identify.cluster_id, MultistateInputCluster],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    AnalogInput.cluster_id,
                    MultistateInputCluster,
                    OnOff.cluster_id,
                ],
            },
        },
    }

    device_automation_triggers = {
        (DOUBLE_PRESS, BUTTON_1): {COMMAND: LEFT_DOUBLE, ENDPOINT_ID: 1},
        (SHORT_PRESS, BUTTON_1): {COMMAND: LEFT_SINGLE, ENDPOINT_ID: 1},
        (LONG_PRESS, BUTTON_1): {COMMAND: LEFT_HOLD, ENDPOINT_ID: 1},
        (DOUBLE_PRESS, BUTTON_2): {COMMAND: RIGHT_DOUBLE, ENDPOINT_ID: 2},
        (SHORT_PRESS, BUTTON_2): {COMMAND: RIGHT_SINGLE, ENDPOINT_ID: 2},
        (LONG_PRESS, BUTTON_2): {COMMAND: RIGHT_HOLD, ENDPOINT_ID: 2},
        (DOUBLE_PRESS, BOTH_BUTTONS): {COMMAND: BOTH_DOUBLE, ENDPOINT_ID: 3},
        (SHORT_PRESS, BOTH_BUTTONS): {COMMAND: BOTH_SINGLE, ENDPOINT_ID: 3},
        (LONG_PRESS, BOTH_BUTTONS): {COMMAND: BOTH_HOLD, ENDPOINT_ID: 3},
    }
