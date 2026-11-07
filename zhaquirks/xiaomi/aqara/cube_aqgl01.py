"""Xiaomi aqara magic cube device."""

import logging
from typing import Final

from zigpy import types as t
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    AnalogInput,
    Groups,
    Identify,
    MultistateInput,
    OnOff,
    Ota,
    Scenes,
)
from zigpy.zcl.foundation import DataTypeId, Status, TypeValue, ZCLAttributeDef

from zhaquirks import CustomCluster
from zhaquirks.builder import EntityPlatform, EntityType, QuirkBuilder
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
from zhaquirks.device import CustomZigpyDevice
from zhaquirks.xiaomi import (
    LUMI,
    XIAOMI_AQARA_ATTRIBUTE_E1,
    BasicCluster,
    DeviceTemperatureCluster,
    XiaomiAqaraE1Cluster,
    XiaomiCustomDevice,
    XiaomiPowerConfiguration,
)

_LOGGER = logging.getLogger(__name__)

ACTIVATED_FACE = "activated_face"
DEACTIVATED_FACE = "deactivated_face"
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
FLIP_TO_SIDE = "flip_to_side"
FLIP_TO_SIDE_BEGIN = 1024
FLIP_TO_SIDE_END = 1030
FLIPPED = "device_flipped"
FLIPPED_TO_SIDE = "device_flipped_to_side"
HELD = "device_held"
HOLD = "hold"
HOLD_VALUE = 4
INACTIVITY = "1_min_inactivity"
INACTIVITY_VALUE = 2
KNOCK = "knock"

KNOCK_1_VALUE = 512  # aqara skyside
KNOCK_2_VALUE = 513  # aqara facing me 90 right
KNOCK_3_VALUE = 514  # aqara facing me upside down
KNOCK_4_VALUE = 515  # aqara tableside
KNOCK_5_VALUE = 516  # aqara facing me 90 left
KNOCK_6_VALUE = 517  # aqara facing me upright

KNOCKED = "device_knocked"
LEFT = "left"
MOVED_AFTER_INACTIVITY = "device_moved_after_inactivity"
OPERATION_MODE_ENDPOINT_ID = 1
OPERATION_MODE_TAG = 155
PENDING_OPERATION_MODE_ATTR = "pending_cube_t1_operation_mode"
RELATIVE_DEGREES = "relative_degrees"
RIGHT = "right"
ROTATE_LEFT = "rotate_left"
ROTATE_RIGHT = "rotate_right"
ROTATED = "device_rotated"
SHAKE = "shake"
SHAKE_VALUE = 0
SIDE_UP = "side_up"
SIDE_UPPED = "device_side_up"
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
XIAOMI_MANUFACTURER_CODE = 0x115F
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
    SLIDE_4_VALUE: "aqara logo on bottom",
    SLIDE_5_VALUE: "aqara logo facing user rotated 90 degrees left",
    SLIDE_6_VALUE: "aqara logo facing user upright",
    KNOCK_1_VALUE: "aqara logo on top",
    KNOCK_2_VALUE: "aqara logo facing user rotated 90 degrees right",
    KNOCK_3_VALUE: "aqara logo facing user upside down",
    KNOCK_4_VALUE: "aqara logo on bottom",
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


def extend_dict(dictionary, value, ranges):
    """Extend a dict."""
    for item in ranges:
        dictionary[item] = value


extend_dict(MOVEMENT_TYPE, FLIP, range(FLIP_BEGIN, FLIP_END))


def parse_operation_mode_tag(value: bytes) -> int | None:
    """Extract the operation_mode tag from a Xiaomi structured attribute report.

    Parses the raw tag/value blob directly instead of using
    `XiaomiCluster._parse_aqara_attributes()`'s per-model dispatch table, so
    this quirk stays self-contained in this single file.
    """
    while value not in (b"", b"\x00"):
        tag = value[0]
        type_value, value = TypeValue.deserialize(value[1:])
        if tag == OPERATION_MODE_TAG:
            return type_value.value
    return None


class MultistateInputCluster(CustomCluster, MultistateInput):
    """Multistate input cluster."""

    # Subclasses may override this to map additional/different raw values,
    # since the same raw value can mean different things on different cubes.
    MOVEMENT_TYPE = MOVEMENT_TYPE

    def __init__(self, *args, **kwargs):
        """Init."""
        self._current_state = {}
        super().__init__(*args, **kwargs)

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == STATUS_TYPE_ATTR:
            self._current_state[STATUS_TYPE_ATTR] = action = self.MOVEMENT_TYPE.get(
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
                        event_args[DEACTIVATED_FACE] = (value // 8) % 8 + 1
                    event_args[ACTIVATED_FACE] = int((value % 8) + 1)

                if action == FLIP_TO_SIDE:
                    event_args[ACTIVATED_FACE] = value - FLIP_TO_SIDE_BEGIN + 1

                self.listener_event(ZHA_SEND_EVENT, action, event_args)

            # show something in the sensor in HA
            super()._update_attribute(0, action)


class CubeT1MultistateInputCluster(MultistateInputCluster):
    """Multistate input cluster for the Aqara T1 cube.

    Raw value 2 means the cube was moved after standing still for a minute,
    unlike the older cube (CubeAQGL01), where the same raw value means
    "wakeup" instead. Raw value 4 (hold) is also specific to the T1, as are raw
    values 1024 to 1029 (flip to side 1 to 6): reported in scene mode, when the
    cube is picked up and put back, on the same face or on another one.
    """

    MOVEMENT_TYPE = {
        **MOVEMENT_TYPE,
        INACTIVITY_VALUE: INACTIVITY,
        HOLD_VALUE: HOLD,
        **dict.fromkeys(range(FLIP_TO_SIDE_BEGIN, FLIP_TO_SIDE_END), FLIP_TO_SIDE),
    }


class CubeT1PowerConfiguration(XiaomiPowerConfiguration):
    """Power configuration cluster matching the Aqara T1 cube's battery voltage range."""

    MIN_VOLTS_MV = 2850
    MAX_VOLTS_MV = 3000


class CubeT1OperationMode(t.enum8):
    """Aqara T1 cube operation mode."""

    action_mode = 0x00
    scene_mode = 0x01


class CubeT1ManufacturerCluster(XiaomiAqaraE1Cluster):
    """Aqara manufacturer specific cluster for the T1 cube.

    The T1 cube reports manufacturer specific attributes as individual
    attributes on this cluster instead of using the legacy Xiaomi attribute
    blob on the Basic cluster. This cluster is not present in the device's
    signature, but the device communicates on it regardless, from both
    endpoint 1 (e.g. battery voltage) and endpoint 2 (e.g. side_up).
    """

    class AttributeDefs(XiaomiAqaraE1Cluster.AttributeDefs):
        """Attribute definitions."""

        battery_voltage_mv: Final = ZCLAttributeDef(
            id=0x0001, type=t.uint16_t, manufacturer_code=XIAOMI_MANUFACTURER_CODE
        )

        # Reported in scene_mode with the face currently facing up, e.g. when the
        # cube wakes up after being bumped on the table. Not to be confused with
        # flip_to_side, which is reported when the cube is picked up and put back.
        side_up: Final = ZCLAttributeDef(
            id=0x0149, type=t.uint8_t, manufacturer_code=XIAOMI_MANUFACTURER_CODE
        )

        # Local cache of the cube's operation mode, updated from the cube's
        # periodic check-in (see `_handle_attribute_event`). Starts unset
        # ("unknown") until the first check-in is seen. Writable, but only
        # via `request_operation_mode_flip()` (see there for why). The wire
        # type must be forced to uint8 (0x20): the cube rejects writes
        # encoded as enum8 (0x30, which `type=CubeT1OperationMode` would
        # otherwise imply) with an INVALID_DATA_TYPE response.
        operation_mode: Final = ZCLAttributeDef(
            id=0x0148,
            type=CubeT1OperationMode,
            zcl_type=DataTypeId.uint8,
            manufacturer_code=XIAOMI_MANUFACTURER_CODE,
        )

    def _update_attribute(self, attrid, value):
        if attrid == self.AttributeDefs.battery_voltage_mv.id:
            if hasattr(self.endpoint, "power"):
                self.endpoint.power.battery_reported(value)
        elif attrid == self.AttributeDefs.side_up.id:
            self.listener_event(ZHA_SEND_EVENT, SIDE_UP, {ACTIVATED_FACE: value + 1})
        super()._update_attribute(attrid, value)

    def _handle_attribute_event(self, event):
        super()._handle_attribute_event(event)
        if event.attribute_id != XIAOMI_AQARA_ATTRIBUTE_E1:
            return

        mode = parse_operation_mode_tag(event.value)
        _LOGGER.debug(
            "Cube T1 check-in: endpoint=%s operation_mode tag=%s",
            self.endpoint.endpoint_id,
            mode,
        )
        if mode is None:
            return

        # The check-in may arrive via either endpoint 1 or 2 (both carry this
        # cluster), but the operation_mode sensor entity is only declared on
        # endpoint 1 - always update that instance regardless of which one
        # actually received the report.
        sensor_cluster = self.endpoint.device.endpoints[
            OPERATION_MODE_ENDPOINT_ID
        ].opple_cluster

        pending = getattr(self.endpoint.device, PENDING_OPERATION_MODE_ATTR, None)
        if pending is None:
            sensor_cluster.update_attribute(self.AttributeDefs.operation_mode.id, mode)
            return

        _LOGGER.debug("Cube T1 check-in: applying pending operation_mode=%s", pending)
        self.create_catching_task(
            self._apply_pending_operation_mode(sensor_cluster, pending)
        )

    async def request_operation_mode_flip(self):
        """Queue a request to flip operation_mode to the other value.

        The cube only listens for this write during a brief window that
        opens on its own roughly once an hour (or immediately after a
        forceful throw, or opening the lid and pressing LINK once). The
        actual write is sent from `_handle_attribute_event()`, once the next
        check-in confirms the cube is listening.
        """
        current = self.get(self.AttributeDefs.operation_mode.name)
        if current is None:
            _LOGGER.debug(
                "Cube T1 operation_mode flip requested but current mode is unknown; ignoring"
            )
            return

        target = (
            CubeT1OperationMode.scene_mode
            if current == CubeT1OperationMode.action_mode
            else CubeT1OperationMode.action_mode
        )
        setattr(self.endpoint.device, PENDING_OPERATION_MODE_ATTR, target)
        _LOGGER.debug(
            "Cube T1 operation_mode flip requested: endpoint=%s current=%s target=%s",
            self.endpoint.endpoint_id,
            current,
            target,
        )

    async def _apply_pending_operation_mode(self, sensor_cluster, value):
        """Send a queued operation_mode write, now that the cube is listening.

        The pending value is only cleared once the write is confirmed to
        have succeeded, so a failed attempt (bad status or a transport
        exception) is retried on the cube's next check-in.
        """
        result = await self.write_attributes(
            {self.AttributeDefs.operation_mode.id: value}
        )
        _LOGGER.debug(
            "Cube T1 operation_mode write result for mode=%s: %s", value, result
        )
        if result[0][0].status != Status.SUCCESS:
            return
        sensor_cluster.update_attribute(self.AttributeDefs.operation_mode.id, value)
        # Check-ins may arrive on both endpoints at about the same time, each
        # starting a write: the one finishing last must not fail on an
        # already cleared value.
        setattr(self.endpoint.device, PENDING_OPERATION_MODE_ATTR, None)


class AnalogInputCluster(CustomCluster, AnalogInput):
    """Analog input cluster."""

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


class CubeT1Device(CustomZigpyDevice):
    """Aqara T1 magic cube device with the correct battery size."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.battery_size = BatterySize.CR2450


#  <SimpleDescriptor endpoint=1 profile=260 device_type=259
#  device_version=1
#  input_clusters=[0, 1, 3, 6, 18]
#  output_clusters=[0, 3, 25]>
#  <SimpleDescriptor endpoint=2 profile=260 device_type=259
#  device_version=1
#  input_clusters=[18]
#  output_clusters=[18]>
#  <SimpleDescriptor endpoint=3 profile=260 device_type=259
#  device_version=1
#  input_clusters=[12]
#  output_clusters=[12]>
(
    QuirkBuilder(LUMI, "lumi.remote.cagl02")
    .zigpy_device_class(CubeT1Device)
    .replaces_endpoint(1, device_type=XIAOMI_SENSORS_REPLACEMENT)
    .replaces(BasicCluster, endpoint_id=1)
    .replaces(CubeT1PowerConfiguration, endpoint_id=1)
    .removes(OnOff.cluster_id, endpoint_id=1)
    # The cube only has OTA as an output (client) cluster; also exposing it as an
    # input (server) cluster is what this quirk has always done, so keep it.
    .adds(Ota.cluster_id, endpoint_id=1)
    .adds(CubeT1ManufacturerCluster, endpoint_id=1)
    .replaces_endpoint(2, device_type=XIAOMI_SENSORS_REPLACEMENT)
    .replaces(CubeT1MultistateInputCluster, endpoint_id=2)
    .adds(CubeT1ManufacturerCluster, endpoint_id=2)
    .replaces_endpoint(3, device_type=XIAOMI_SENSORS_REPLACEMENT)
    .replaces(AnalogInputCluster, endpoint_id=3)
    .enum(
        attribute_name=CubeT1ManufacturerCluster.AttributeDefs.operation_mode.name,
        enum_class=CubeT1OperationMode,
        cluster_id=CubeT1ManufacturerCluster.cluster_id,
        endpoint_id=OPERATION_MODE_ENDPOINT_ID,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="operation_mode",
        fallback_name="Operation mode",
    )
    .command_button(
        command_name="request_operation_mode_flip",
        cluster_id=CubeT1ManufacturerCluster.cluster_id,
        endpoint_id=OPERATION_MODE_ENDPOINT_ID,
        translation_key="request_operation_mode_flip",
        fallback_name="Flip operation mode",
    )
    .device_automation_triggers(
        {
            **CubeAQGL01.device_automation_triggers,
            (HELD, TURN_ON): {COMMAND: HOLD},
            (MOVED_AFTER_INACTIVITY, TURN_ON): {COMMAND: INACTIVITY},
            (FLIPPED_TO_SIDE, FACE_ANY): {COMMAND: FLIP_TO_SIDE},
            (FLIPPED_TO_SIDE, FACE_1): {
                COMMAND: FLIP_TO_SIDE,
                ARGS: {ACTIVATED_FACE: 1},
            },
            (FLIPPED_TO_SIDE, FACE_2): {
                COMMAND: FLIP_TO_SIDE,
                ARGS: {ACTIVATED_FACE: 2},
            },
            (FLIPPED_TO_SIDE, FACE_3): {
                COMMAND: FLIP_TO_SIDE,
                ARGS: {ACTIVATED_FACE: 3},
            },
            (FLIPPED_TO_SIDE, FACE_4): {
                COMMAND: FLIP_TO_SIDE,
                ARGS: {ACTIVATED_FACE: 4},
            },
            (FLIPPED_TO_SIDE, FACE_5): {
                COMMAND: FLIP_TO_SIDE,
                ARGS: {ACTIVATED_FACE: 5},
            },
            (FLIPPED_TO_SIDE, FACE_6): {
                COMMAND: FLIP_TO_SIDE,
                ARGS: {ACTIVATED_FACE: 6},
            },
            (SIDE_UPPED, FACE_ANY): {COMMAND: SIDE_UP},
            (SIDE_UPPED, FACE_1): {COMMAND: SIDE_UP, ARGS: {ACTIVATED_FACE: 1}},
            (SIDE_UPPED, FACE_2): {COMMAND: SIDE_UP, ARGS: {ACTIVATED_FACE: 2}},
            (SIDE_UPPED, FACE_3): {COMMAND: SIDE_UP, ARGS: {ACTIVATED_FACE: 3}},
            (SIDE_UPPED, FACE_4): {COMMAND: SIDE_UP, ARGS: {ACTIVATED_FACE: 4}},
            (SIDE_UPPED, FACE_5): {COMMAND: SIDE_UP, ARGS: {ACTIVATED_FACE: 5}},
            (SIDE_UPPED, FACE_6): {COMMAND: SIDE_UP, ARGS: {ACTIVATED_FACE: 6}},
        }
    )
    .add_to_registry()
)
