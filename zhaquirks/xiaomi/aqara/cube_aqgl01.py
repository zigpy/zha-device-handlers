"""Xiaomi aqara magic cube device."""

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    AnalogInput,
    Groups,
    Identify,
    MultistateInput,
    OnOff,
    Ota,
    PowerConfiguration,
    Scenes,
)

from zhaquirks import CustomCluster
from zhaquirks.const import (
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
    BatterySize,
)
from zhaquirks.xiaomi import (
    LUMI,
    BasicCluster,
    DeviceTemperatureCluster,
    XiaomiCustomDevice,
    XiaomiPowerConfiguration,
)

STATUS_TYPE_ATTR = 0x0055  # decimal = 85
XIAOMI_ANALOG = 0x5F03  # decimal = 24323 ? analog input
XIAOMI_ANALOG_REPLACEMENT = 0x6F03
XIAOMI_MEASUREMENTS = 0x5F02  # decimal = 24322 ? multistate measurements
XIAOMI_MEASUREMENTS_REPLACEMENT = 0x6F02
XIAOMI_SENSORS = 0x5F01  # decimal = 24321 ? sensors
XIAOMI_SENSORS_REPLACEMENT = 0x6F01

# Keywords
DESCRIPTION = "description"
ACTIVATED_FACE = "activated_face"
DEACTIVATED_FACE = "deactivated_face"
FLIP_DEGREES = "flip_degrees"

# Discrete events:
SHAKE = "shake"
DROP = "drop"
FLIP_90 = "flip_90"
FLIP_180 = "flip_180"
SLIDE = "slide"
KNOCK = "knock"
SCENE = "scene"
UNKNOWN = "unknown"
FLIP = "flip"

# Analog events:
LEFT = "left"
RELATIVE_DEGREES = "relative_degrees"
RIGHT = "right"
ROTATE_LEFT = "rotate_left"
ROTATE_RIGHT = "rotate_right"
ROTATED = "device_rotated"

# Automation triggers:
DROPPED = "device_dropped"
FLIPPED = "device_flipped"
KNOCKED = "device_knocked"
SLID = "device_slid"
SCENE_CHANGED = "device_scene_change"

FACE_ANY = "face_any"
FACE_1 = "face_1"
FACE_2 = "face_2"
FACE_3 = "face_3"
FACE_4 = "face_4"
FACE_5 = "face_5"
FACE_6 = "face_6"


MOVEMENT_TYPE = {
    0: SHAKE,  # Doesn't include an activated face
    3: DROP,  # Have to special-case this as it doesn't follow the rules.
    # Never seen bit 16
    # Bit 32 appears in FLIP_90 events, not sure why - possibly clockwise / anti-clockwise?
    64: FLIP_90,
    128: FLIP_180,
    256: SLIDE,
    512: KNOCK,  # Seems VERY unreliable
    1024: SCENE,  # A bit like FLIP, but fired in scene mode.
}


class MultistateInputCluster(CustomCluster, MultistateInput):
    """Multistate input cluster."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self._current_state = {}
        super().__init__(*args, **kwargs)

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == STATUS_TYPE_ATTR:  # 0x55
            # Bitwise split: The lowest bits represent the face, the higher bits represent the type of movement
            # +1 because we want to count faces from 1 to 6, not from 0 to 5
            activated_face = (value & 0x7) + 1
            deactivated_face = ((value >> 3) & 0x7) + 1  # Only applies to FLIP_90

            # Zero-out the lowest 8 bits to get the movement type
            movement = value & 0xFFC0

            if movement == 0:
                # SHAKE and DROP don't seem to have activated_face attributes.
                action = MOVEMENT_TYPE.get(value)
            else:
                action = MOVEMENT_TYPE.get(movement)
            self._current_state[STATUS_TYPE_ATTR] = action

            event_args = {VALUE: value}
            if action is not None:
                if action in (SHAKE, DROP):
                    # No args for these events.
                    pass
                else:
                    # All other actions have an ACTIVATED_FACE:
                    event_args[ACTIVATED_FACE] = activated_face

                    # Only flips have a DEACTIVATED_FACE and FLIP_DEGREES:
                    if action in [FLIP_180]:
                        event_args[FLIP_DEGREES] = 180
                        # Opposite sides add up to 7
                        event_args[DEACTIVATED_FACE] = 7 - activated_face
                        action = FLIP
                    if action in [FLIP_90]:
                        event_args[FLIP_DEGREES] = 90
                        event_args[DEACTIVATED_FACE] = deactivated_face
                        action = FLIP

                self.listener_event(ZHA_SEND_EVENT, action, event_args)

            # show something in the sensor in HA
            # Though I think post: https://github.com/home-assistant/core/pull/36696 this is no-longer meaningful
            super()._update_attribute(0, action)


class AnalogInputCluster(CustomCluster, AnalogInput):
    """Analog input cluster."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)

        if attrid == STATUS_TYPE_ATTR:
            if value > 0:
                action = ROTATE_RIGHT
            else:
                action = ROTATE_LEFT

            # show something in the sensor in HA
            super()._update_attribute(0, action)

            if action is not None:
                self.listener_event(
                    ZHA_SEND_EVENT,
                    action,
                    {RELATIVE_DEGREES: value},
                )


class CubeAQGL01(XiaomiCustomDevice):
    """Aqara magic cube device."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.battery_size = BatterySize.CR2450
        super().__init__(*args, **kwargs)

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
                    XiaomiPowerConfiguration,
                    DeviceTemperatureCluster,
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
                # There's also a secret Xaiaomi 0xfcc0 cluster in this endpoint, not yet implemented.
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
        (SCENE_CHANGED, FACE_ANY): {COMMAND: SCENE},
        (SCENE_CHANGED, FACE_1): {COMMAND: SCENE, ARGS: {ACTIVATED_FACE: 1}},
        (SCENE_CHANGED, FACE_2): {COMMAND: SCENE, ARGS: {ACTIVATED_FACE: 2}},
        (SCENE_CHANGED, FACE_3): {COMMAND: SCENE, ARGS: {ACTIVATED_FACE: 3}},
        (SCENE_CHANGED, FACE_4): {COMMAND: SCENE, ARGS: {ACTIVATED_FACE: 4}},
        (SCENE_CHANGED, FACE_5): {COMMAND: SCENE, ARGS: {ACTIVATED_FACE: 5}},
        (SCENE_CHANGED, FACE_6): {COMMAND: SCENE, ARGS: {ACTIVATED_FACE: 6}},
    }


class CubeCAGL02(XiaomiCustomDevice):
    """Aqara T1 magic cube device."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.battery_size = BatterySize.CR2450
        super().__init__(*args, **kwargs)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=259
        #  device_version=1
        #  input_clusters=[0, 1, 3, 6, 18]
        #  output_clusters=[0, 3, 25]>
        MODELS_INFO: [(LUMI, "lumi.remote.cagl02")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    BasicCluster.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    MultistateInput.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    BasicCluster.cluster_id,
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            },
            #  <SimpleDescriptor endpoint=2 profile=260 device_type=259
            #  device_version=1
            #  input_clusters=[18]
            #  output_clusters=[18]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [MultistateInput.cluster_id],
                OUTPUT_CLUSTERS: [
                    MultistateInput.cluster_id,
                ],
            },
            #  <SimpleDescriptor endpoint=3 profile=260 device_type=259
            #  device_version=1
            #  input_clusters=[12]
            #  output_clusters=[12]>
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [AnalogInput.cluster_id],
                OUTPUT_CLUSTERS: [
                    AnalogInput.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: XIAOMI_SENSORS_REPLACEMENT,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    XiaomiPowerConfiguration,
                    Identify.cluster_id,
                    Ota.cluster_id,
                    MultistateInput.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    BasicCluster.cluster_id,
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            },
            2: {
                DEVICE_TYPE: XIAOMI_SENSORS_REPLACEMENT,
                INPUT_CLUSTERS: [MultistateInputCluster],
                OUTPUT_CLUSTERS: [
                    MultistateInput.cluster_id,
                ],
            },
            3: {
                DEVICE_TYPE: XIAOMI_SENSORS_REPLACEMENT,
                INPUT_CLUSTERS: [AnalogInputCluster],
                OUTPUT_CLUSTERS: [
                    AnalogInput.cluster_id,
                ],
            },
        },
    }

    device_automation_triggers = CubeAQGL01.device_automation_triggers
