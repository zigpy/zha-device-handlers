"""Xiaomi aqara smart vibration sensor device."""

import math
from typing import Final

from zigpy import types
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.closures import DoorLock
from zigpy.zcl.clusters.general import MultistateInput
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import DataTypeId, ZCLAttributeDef

from zhaquirks import Bus, LocalDataCluster, MotionOnEvent
from zhaquirks.builder import DEGREE, QuirkBuilder, SensorStateClass
from zhaquirks.clusters import CustomCluster
from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_TILT,
    ENDPOINT_ID,
    MOTION_EVENT,
    UNKNOWN,
    ZHA_SEND_EVENT,
    ZONE_TYPE,
)
from zhaquirks.device import CustomZigpyDevice
from zhaquirks.xiaomi import (
    LUMI,
    BasicCluster,
    BatterySize,
    DeviceTemperatureCluster,
    XiaomiPowerConfiguration,
)

DROP_VALUE = 3
ORIENTATION_ATTR = 0x0508  # decimal = 1288
RECENT_ACTIVITY_LEVEL_ATTR = 0x0505  # decimal = 1285
ROTATION_DEGREES_ATTR = 0x0503  # decimal = 1283
SEND_EVENT = "send_event"
STATIONARY_VALUE = 0
STATUS_TYPE_ATTR = 0x0055  # decimal = 85
TILT_VALUE = 2
DROPPED = "device_dropped"
TILTED = "device_tilted"
VIBE_VALUE = 1

MEASUREMENT_TYPE = {
    STATIONARY_VALUE: "Stationary",
    VIBE_VALUE: "Vibration",
    TILT_VALUE: "Tilt",
    DROP_VALUE: "Drop",
}


class VibrationSensitivity(types.enum8):
    """Vibration sensor sensitivity, lower raw values are more sensitive."""

    Low = 0x15
    Medium = 0x0B
    High = 0x01


def vibration_strength(value: int) -> int:
    """Extract the vibration strength from the recent activity level report."""
    strength = value >> 8
    return ((strength & 0xFF) << 8) | ((strength >> 8) & 0xFF)


class VibrationAQ1(CustomZigpyDevice):
    """Xiaomi aqara smart vibration sensor device."""

    battery_size = BatterySize.CR2032
    manufacturer_id_override = 0x115F

    def __init__(self, *args, **kwargs):
        """Init."""
        self.motion_bus = Bus()
        super().__init__(*args, **kwargs)


class VibrationBasicCluster(BasicCluster):
    """Vibration sensor Basic cluster."""

    class AttributeDefs(BasicCluster.AttributeDefs):
        """Attribute definitions."""

        sensitivity: Final = ZCLAttributeDef(
            id=0xFF0D,
            type=VibrationSensitivity,
            zcl_type=DataTypeId.uint8,
            access="rw",
            manufacturer_code=0x115F,
        )


class MultistateInputCluster(CustomCluster, MultistateInput):
    """Multistate input cluster, the device reports it with the DoorLock id."""

    cluster_id = DoorLock.cluster_id

    class AttributeDefs(MultistateInput.AttributeDefs):
        """Attribute definitions."""

        tilt_angle: Final = ZCLAttributeDef(
            id=ROTATION_DEGREES_ATTR,
            type=types.uint16_t,
            access="rp",
            manufacturer_code=None,
        )
        recent_activity_level: Final = ZCLAttributeDef(
            id=RECENT_ACTIVITY_LEVEL_ATTR,
            type=types.uint32_t,
            access="rp",
            manufacturer_code=None,
        )

    def __init__(self, *args, **kwargs):
        """Init."""
        self._current_state = {}
        super().__init__(*args, **kwargs)

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == STATUS_TYPE_ATTR:
            self._current_state[STATUS_TYPE_ATTR] = MEASUREMENT_TYPE.get(value, UNKNOWN)
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
            self.endpoint.device.motion_bus.listener_event(
                SEND_EVENT,
                "vibration_strength",
                {"strength": vibration_strength(value)},
            )


class MotionCluster(LocalDataCluster, MotionOnEvent):
    """Aqara Vibration Sensor."""

    _CONSTANT_ATTRIBUTES = {ZONE_TYPE: IasZone.ZoneType.Vibration_Movement_Sensor}
    reset_s = 70

    def send_event(self, event, *args):
        """Send event."""
        self.listener_event(ZHA_SEND_EVENT, event, *args)


(
    QuirkBuilder(LUMI, "lumi.vibration.aq1")
    .zigpy_device_class(VibrationAQ1)
    .skip_configuration()
    .replaces(VibrationBasicCluster)
    .replaces(VibrationBasicCluster, cluster_type=ClusterType.Client)
    .adds(XiaomiPowerConfiguration)
    .adds(DeviceTemperatureCluster)
    .adds(MotionCluster)
    .replaces(MultistateInputCluster)
    # the DoorLock client cluster is really the MultistateInput cluster above
    .removes(DoorLock.cluster_id, cluster_type=ClusterType.Client)
    .removes(MultistateInput.cluster_id, endpoint_id=2)
    .enum(
        VibrationBasicCluster.AttributeDefs.sensitivity.name,
        VibrationSensitivity,
        VibrationBasicCluster.cluster_id,
        translation_key="sensitivity",
        fallback_name="Sensitivity",
    )
    .sensor(
        MultistateInputCluster.AttributeDefs.tilt_angle.name,
        MultistateInputCluster.cluster_id,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        unit=DEGREE,
        translation_key="tilt_angle",
        fallback_name="Tilt angle",
    )
    .sensor(
        MultistateInputCluster.AttributeDefs.recent_activity_level.name,
        MultistateInputCluster.cluster_id,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        attribute_converter=vibration_strength,
        unique_id_suffix="vibration_strength",
        translation_key="vibration_strength",
        fallback_name="Vibration strength",
    )
    .device_automation_triggers(
        {
            (TILTED, TILTED): {COMMAND: COMMAND_TILT, CLUSTER_ID: 1280, ENDPOINT_ID: 1},
            (DROPPED, DROPPED): {
                COMMAND: MEASUREMENT_TYPE[DROP_VALUE],
                CLUSTER_ID: 1280,
                ENDPOINT_ID: 1,
            },
        }
    )
    .add_to_registry()
)
