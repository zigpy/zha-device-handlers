"""Xiaomi aqara magic cube device."""
import logging

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    AnalogInput,
    Groups,
    Identify,
    MultistateInput,
    Ota,
    Scenes,
)

from .. import LUMI, BasicCluster, PowerConfigurationCluster, XiaomiCustomDevice
from ... import CustomCluster
from ...const import (
    ARGS,
    COMMAND,
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHAKEN,
    SKIP_CONFIGURATION,
    TURN_ON,
    VALUE,
    ZHA_SEND_EVENT,
)

ACTIVATED_FACE = "activated_face"
DESCRIPTION = "description"
DROP = "drop"
DROP_VALUE = 3
DROPPED = "device_dropped"

FACE_ANY = "face_any"
FACE_1 = "face_1"
FACE_2 = "face_2"
FACE_3 = "face_3"
FACE_4 = "face_4"
FACE_5 = "face_5"
FACE_6 = "face_6"

FLIP = "flip"
FLIP_BEGIN = 50
FLIP_DEGREES = "flip_degrees"
FLIP_END = 180
FLIPPED = "device_flipped"
KNOCK = "knock"

KNOCK_1_VALUE = 512  # aqara skyside
KNOCK_2_VALUE = 513  # aqara facing me 90 right
KNOCK_3_VALUE = 514  # aqara facing me upside down
KNOCK_4_VALUE = 515  # aqara tableside
KNOCK_5_VALUE = 516  # aqara facing me 90 left
KNOCK_6_VALUE = 517  # aqara facing me upright

KNOCKED = "device_knocked"
LEFT = "left"
RELATIVE_DEGREES = "relative_degrees"
RIGHT = "right"
ROTATE_LEFT = "rotate_left"
ROTATE_RIGHT = "rotate_right"
ROTATED = "device_rotated"
SHAKE = "shake"
SHAKE_VALUE = 0
SLID = "device_slid"
SLIDE = "slide"

SLIDE_1_VALUE = 256  # aqara skyside
SLIDE_2_VALUE = 257  # aqara facing me 90 right
SLIDE_3_VALUE = 258  # aqara facing me upside down
SLIDE_4_VALUE = 259  # aqara tableside
SLIDE_5_VALUE = 260  # aqara facing me 90 left
SLIDE_6_VALUE = 261  # aqara facing me upright

SLIDE_VALUE = 261
STATUS_TYPE_ATTR = 0x0055  # decimal = 85
XIAOMI_ANALOG = 0x5F03  # decimal = 24323 ? analog input
XIAOMI_ANALOG_REPLACEMENT = 0x6F03
XIAOMI_MEASUREMENTS = 0x5F02  # decimal = 24322 ? multistate measurements
XIAOMI_MEASUREMENTS_REPLACEMENT = 0x6F02
XIAOMI_SENSORS = 0x5F01  # decimal = 24321 ? sensors
XIAOMI_SENSORS_REPLACEMENT = 0x6F01

MOVEMENT_TYPE = {
    SHAKE_VALUE: SHAKE,
    DROP_VALUE: DROP,
    SLIDE_1_VALUE: SLIDE,
    SLIDE_2_VALUE: SLIDE,
    SLIDE_3_VALUE: SLIDE,
    SLIDE_4_VALUE: SLIDE,
    SLIDE_5_VALUE: SLIDE,
    SLIDE_6_VALUE: SLIDE,
    KNOCK_1_VALUE: KNOCK,
    KNOCK_2_VALUE: KNOCK,
    KNOCK_3_VALUE: KNOCK,
    KNOCK_4_VALUE: KNOCK,
    KNOCK_5_VALUE: KNOCK,
    KNOCK_6_VALUE: KNOCK,
}

MOVEMENT_TYPE_DESCRIPTION = {
    SHAKE_VALUE: SHAKE,
    DROP_VALUE: DROP,
    SLIDE_1_VALUE: "aqara logo on top",
    SLIDE_2_VALUE: "aqara logo facing user rotated 90 degrees right",
    SLIDE_3_VALUE: "aqara logo facing user upside down",
    SLIDE_4_VALUE: "arara logo on bottom",
    SLIDE_5_VALUE: "aqara logo facing user rotated 90 degrees left",
    SLIDE_6_VALUE: "aqara logo facing user upright",
    KNOCK_1_VALUE: "aqara logo on top",
    KNOCK_2_VALUE: "aqara logo facing user rotated 90 degrees right",
    KNOCK_3_VALUE: "aqara logo facing user upside down",
    KNOCK_4_VALUE: "arara logo on bottom",
    KNOCK_5_VALUE: "aqara logo facing user rotated 90 degrees left",
    KNOCK_6_VALUE: "aqara logo facing user upright",
}

SIDES = {
    SLIDE_1_VALUE: 1,
    SLIDE_2_VALUE: 2,
    SLIDE_3_VALUE: 3,
    SLIDE_4_VALUE: 4,
    SLIDE_5_VALUE: 5,
    SLIDE_6_VALUE: 6,
    KNOCK_1_VALUE: 1,
    KNOCK_2_VALUE: 2,
    KNOCK_3_VALUE: 3,
    KNOCK_4_VALUE: 4,
    KNOCK_5_VALUE: 5,
    KNOCK_6_VALUE: 6,
}

_LOGGER = logging.getLogger(__name__)


def extend_dict(dictionary, value, ranges):
    """Extend a dict."""
    for item in ranges:
        dictionary[item] = value


extend_dict(MOVEMENT_TYPE, FLIP, range(FLIP_BEGIN, FLIP_END))


class CubeAQGL01(XiaomiCustomDevice):
    """Aqara magic cube device."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.battery_size = 9
        super().__init__(*args, **kwargs)

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
                self._current_state[STATUS_TYPE_ATTR] = action = MOVEMENT_TYPE.get(
                    value
                )
                event_args = {VALUE: value}
                if action is not None:

                    if action in (SLIDE, KNOCK):
                        event_args[DESCRIPTION] = MOVEMENT_TYPE_DESCRIPTION[value]
                        event_args[ACTIVATED_FACE] = SIDES[value]

                    if action == FLIP:
                        if value > 108:
                            event_args[FLIP_DEGREES] = 180
                        else:
                            event_args[FLIP_DEGREES] = 90
                        event_args[ACTIVATED_FACE] = (value % 8) + 1

                    self.listener_event(ZHA_SEND_EVENT, action, event_args)

                # show something in the sensor in HA
                super()._update_attribute(0, action)

    class AnalogInputCluster(CustomCluster, AnalogInput):
        """Analog input cluster."""

        cluster_id = AnalogInput.cluster_id

        def __init__(self, *args, **kwargs):
            """Init."""
            self._current_state = {}
            super().__init__(*args, **kwargs)

        def _update_attribute(self, attrid, value):
            super()._update_attribute(attrid, value)
            if attrid == STATUS_TYPE_ATTR:
                if value > 0:
                    self._current_state[STATUS_TYPE_ATTR] = ROTATE_RIGHT
                else:
                    self._current_state[STATUS_TYPE_ATTR] = ROTATE_LEFT
                # show something in the sensor in HA
                super()._update_attribute(0, value)
                if self._current_state[STATUS_TYPE_ATTR] is not None:
                    self.listener_event(
                        ZHA_SEND_EVENT,
                        self._current_state[STATUS_TYPE_ATTR],
                        {RELATIVE_DEGREES: value},
                    )

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=24321
        #  device_version=1
        #  input_clusters=[0, 3, 25, 18]
        #  output_clusters=[0, 4, 3, 5, 25, 18]>
        MODELS_INFO: [(LUMI, "lumi.sensor_cube.aqgl01")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: XIAOMI_SENSORS,
                INPUT_CLUSTERS: [
                    BasicCluster.cluster_id,
                    Identify.cluster_id,
                    Ota.cluster_id,
                    MultistateInput.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    BasicCluster.cluster_id,
                    Groups.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    Ota.cluster_id,
                    MultistateInput.cluster_id,
                ],
            },
            #  <SimpleDescriptor endpoint=2 profile=260 device_type=24322
            #  device_version=1
            #  input_clusters=[3, 18]
            #  output_clusters=[4, 3, 5, 18]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: XIAOMI_MEASUREMENTS,
                INPUT_CLUSTERS: [Identify.cluster_id, MultistateInput.cluster_id],
                OUTPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    MultistateInput.cluster_id,
                ],
            },
            #  <SimpleDescriptor endpoint=3 profile=260 device_type=24323
            #  device_version=1
            #  input_clusters=[3, 12]
            #  output_clusters=[4, 3, 5, 12]>
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: XIAOMI_ANALOG,
                INPUT_CLUSTERS: [Identify.cluster_id, AnalogInput.cluster_id],
                OUTPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Identify.cluster_id,
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
                DEVICE_TYPE: XIAOMI_SENSORS_REPLACEMENT,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    BasicCluster.cluster_id,
                    Groups.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    Ota.cluster_id,
                    MultistateInput.cluster_id,
                ],
            },
            2: {
                DEVICE_TYPE: XIAOMI_MEASUREMENTS_REPLACEMENT,
                INPUT_CLUSTERS: [Identify.cluster_id, MultistateInputCluster],
                OUTPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    MultistateInput.cluster_id,
                ],
            },
            3: {
                DEVICE_TYPE: XIAOMI_ANALOG_REPLACEMENT,
                INPUT_CLUSTERS: [Identify.cluster_id, AnalogInputCluster],
                OUTPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    AnalogInput.cluster_id,
                ],
            },
        },
    }

    device_automation_triggers = {
        (ROTATED, RIGHT): {COMMAND: ROTATE_RIGHT},
        (ROTATED, LEFT): {COMMAND: ROTATE_LEFT},
        (SHAKEN, TURN_ON): {COMMAND: SHAKE},
        (DROPPED, TURN_ON): {COMMAND: DROP},
        (SLID, FACE_ANY): {COMMAND: SLIDE},
        (SLID, FACE_1): {COMMAND: SLIDE, ARGS: {ACTIVATED_FACE: 1}},
        (SLID, FACE_2): {COMMAND: SLIDE, ARGS: {ACTIVATED_FACE: 2}},
        (SLID, FACE_3): {COMMAND: SLIDE, ARGS: {ACTIVATED_FACE: 3}},
        (SLID, FACE_4): {COMMAND: SLIDE, ARGS: {ACTIVATED_FACE: 4}},
        (SLID, FACE_5): {COMMAND: SLIDE, ARGS: {ACTIVATED_FACE: 5}},
        (SLID, FACE_6): {COMMAND: SLIDE, ARGS: {ACTIVATED_FACE: 6}},
        (KNOCKED, FACE_ANY): {COMMAND: KNOCK},
        (KNOCKED, FACE_1): {COMMAND: KNOCK, ARGS: {ACTIVATED_FACE: 1}},
        (KNOCKED, FACE_2): {COMMAND: KNOCK, ARGS: {ACTIVATED_FACE: 2}},
        (KNOCKED, FACE_3): {COMMAND: KNOCK, ARGS: {ACTIVATED_FACE: 3}},
        (KNOCKED, FACE_4): {COMMAND: KNOCK, ARGS: {ACTIVATED_FACE: 4}},
        (KNOCKED, FACE_5): {COMMAND: KNOCK, ARGS: {ACTIVATED_FACE: 5}},
        (KNOCKED, FACE_6): {COMMAND: KNOCK, ARGS: {ACTIVATED_FACE: 6}},
        (FLIPPED, FACE_ANY): {COMMAND: FLIP},
        (FLIPPED, FACE_1): {COMMAND: FLIP, ARGS: {ACTIVATED_FACE: 1}},
        (FLIPPED, FACE_2): {COMMAND: FLIP, ARGS: {ACTIVATED_FACE: 2}},
        (FLIPPED, FACE_3): {COMMAND: FLIP, ARGS: {ACTIVATED_FACE: 3}},
        (FLIPPED, FACE_4): {COMMAND: FLIP, ARGS: {ACTIVATED_FACE: 4}},
        (FLIPPED, FACE_5): {COMMAND: FLIP, ARGS: {ACTIVATED_FACE: 5}},
        (FLIPPED, FACE_6): {COMMAND: FLIP, ARGS: {ACTIVATED_FACE: 6}},
    }
