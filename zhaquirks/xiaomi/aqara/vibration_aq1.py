"""Xiaomi aqara smart motion sensor device."""
import logging
import math

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster
import zigpy.types as types
from zigpy.zcl.clusters.closures import DoorLock
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    MultistateInput,
    Ota,
    Scenes,
)
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import Bus, LocalDataCluster, MotionOnEvent
from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_TILT,
    DEVICE_TYPE,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    MOTION_EVENT,
    NODE_DESCRIPTOR,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SKIP_CONFIGURATION,
    UNKNOWN,
    ZHA_SEND_EVENT,
    ZONE_TYPE,
)
from zhaquirks.xiaomi import (
    LUMI,
    XIAOMI_NODE_DESC,
    BasicCluster,
    DeviceTemperatureCluster,
    XiaomiPowerConfiguration,
    XiaomiQuickInitDevice,
)

DROP_VALUE = 3
ORIENTATION_ATTR = 0x0508  # decimal = 1288
RECENT_ACTIVITY_LEVEL_ATTR = 0x0505  # decimal = 1285
ROTATION_DEGREES_ATTR = 0x0503  # decimal = 1283
SEND_EVENT = "send_event"
STATIONARY_VALUE = 0
STATUS_TYPE_ATTR = 0x0055  # decimal = 85
TILT_VALUE = 2
TILTED = "device_tilted"
VIBE_DEVICE_TYPE = 0x5F02  # decimal = 24322
VIBE_VALUE = 1

MEASUREMENT_TYPE = {
    STATIONARY_VALUE: "Stationary",
    VIBE_VALUE: "Vibration",
    TILT_VALUE: "Tilt",
    DROP_VALUE: "Drop",
}

_LOGGER = logging.getLogger(__name__)


class VibrationAQ1(XiaomiQuickInitDevice):
    """Xiaomi aqara smart motion sensor device."""

    manufacturer_id_override = 0x115F

    def __init__(self, *args, **kwargs):
        """Init."""
        self.motion_bus = Bus()
        super().__init__(*args, **kwargs)

    class VibrationBasicCluster(BasicCluster):
        """Vibration cluster."""

        attributes = BasicCluster.attributes.copy()
        attributes[0xFF0D] = ("sensitivity", types.uint8_t, True)

    class MultistateInputCluster(CustomCluster, MultistateInput):
        """Multistate input cluster."""

        cluster_id = DoorLock.cluster_id

        def __init__(self, *args, **kwargs):
            """Init."""
            self._current_state = {}
            super().__init__(*args, **kwargs)

        def _update_attribute(self, attrid, value):
            super()._update_attribute(attrid, value)
            if attrid == STATUS_TYPE_ATTR:
                self._current_state[STATUS_TYPE_ATTR] = MEASUREMENT_TYPE.get(
                    value, UNKNOWN
                )
                if value == VIBE_VALUE:
                    self.endpoint.device.motion_bus.listener_event(MOTION_EVENT)
                elif value == DROP_VALUE:
                    self.endpoint.device.motion_bus.listener_event(
                        SEND_EVENT, self._current_state[STATUS_TYPE_ATTR], {}
                    )
            elif attrid == ORIENTATION_ATTR:
                x = value & 0xFFFF
                y = (value >> 16) & 0xFFFF
                z = (value >> 32) & 0xFFFF
                X = 0.0 + x
                Y = 0.0 + y
                Z = 0.0 + z
                angleX = round(math.atan(X / math.sqrt(Z * Z + Y * Y)) * 180 / math.pi)
                angleY = round(math.atan(Y / math.sqrt(X * X + Z * Z)) * 180 / math.pi)
                angleZ = round(math.atan(Z / math.sqrt(X * X + Y * Y)) * 180 / math.pi)

                self.endpoint.device.motion_bus.listener_event(
                    SEND_EVENT,
                    "current_orientation",
                    {
                        "rawValueX": x,
                        "rawValueY": y,
                        "rawValueZ": z,
                        "X": angleX,
                        "Y": angleY,
                        "Z": angleZ,
                    },
                )
            elif attrid == ROTATION_DEGREES_ATTR:
                self.endpoint.device.motion_bus.listener_event(
                    SEND_EVENT,
                    self._current_state[STATUS_TYPE_ATTR],
                    {"degrees": value},
                )
            elif attrid == RECENT_ACTIVITY_LEVEL_ATTR:
                # these seem to be sent every minute when vibration is active
                strength = value >> 8
                strength = ((strength & 0xFF) << 8) | ((strength >> 8) & 0xFF)
                self.endpoint.device.motion_bus.listener_event(
                    SEND_EVENT,
                    "vibration_strength",
                    {"strength": strength},
                )

    class MotionCluster(LocalDataCluster, MotionOnEvent):
        """Aqara Vibration Sensor."""

        _CONSTANT_ATTRIBUTES = {ZONE_TYPE: IasZone.ZoneType.Vibration_Movement_Sensor}
        reset_s = 70

        def send_event(self, event, *args):
            """Send event."""
            self.listener_event(ZHA_SEND_EVENT, event, *args)

    signature = {
        MODELS_INFO: [(LUMI, "lumi.vibration.aq1")],
        NODE_DESCRIPTOR: XIAOMI_NODE_DESC,
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DOOR_LOCK,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Ota.cluster_id,
                    DoorLock.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Ota.cluster_id,
                    DoorLock.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: VIBE_DEVICE_TYPE,
                INPUT_CLUSTERS: [Identify.cluster_id, MultistateInput.cluster_id],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MultistateInput.cluster_id,
                ],
            },
        },
    }

    replacement = {
        SKIP_CONFIGURATION: True,
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.DOOR_LOCK,
                INPUT_CLUSTERS: [
                    VibrationBasicCluster,
                    XiaomiPowerConfiguration,
                    DeviceTemperatureCluster,
                    Identify.cluster_id,
                    MotionCluster,
                    Ota.cluster_id,
                    MultistateInputCluster,
                ],
                OUTPUT_CLUSTERS: [
                    VibrationBasicCluster,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Ota.cluster_id,
                ],
            },
            2: {
                DEVICE_TYPE: VIBE_DEVICE_TYPE,
                INPUT_CLUSTERS: [Identify.cluster_id],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MultistateInput.cluster_id,
                ],
            },
        },
    }

    device_automation_triggers = {
        (TILTED, TILTED): {COMMAND: COMMAND_TILT, CLUSTER_ID: 1280, ENDPOINT_ID: 1}
    }
