"""Aqara Vibration Sensor T1 (DJT12LM) — lumi.vibration.agl01.

Based on nachtaap's quirk from zigpy/zha-device-handlers#4137, enhanced with
MotionCluster for binary_sensor entity.

Data paths observed:
- IAS Zone attr 0x002D on EP2→dst EP1: value=1 vibration, value=2 triple-tap
    -> removed the implementation because it was redundant and seemed to disturb the other two paths
- manuSpecificLumi attr 0x0118 (280) on EP2: value=1 vibration
- MultistateInput presentValue on EP2: value=1 triple-tap

Author: @mengwong. Originally shared as GitHub Gist https://gist.github.com/mengwong/b3ca949249405f99f03dce270d3029f5
in issue https://github.com/zigpy/zha-device-handlers/issues/4137#issuecomment-4205558840
"""

from typing import Final

import zigpy.types as t
from zigpy.zcl.clusters.general import MultistateInput
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import DataTypeId, ZCLAttributeDef

from zhaquirks import Bus, EventableCluster, LocalDataCluster, MotionOnEvent
from zhaquirks.builder import NumberDeviceClass, QuirkBuilder, UnitOfTime
from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    ENDPOINT_ID,
    MOTION_EVENT,
    ZHA_SEND_EVENT,
    ZONE_TYPE,
)
from zhaquirks.device import CustomZigpyDevice
from zhaquirks.xiaomi import (
    LUMI,
    BasicCluster,
    XiaomiAqaraE1Cluster,
    XiaomiPowerConfiguration,
)

# Event types
VIBRATION = "vibration"
TRIPLE_TAP = "triple_tap"

# Xiaomi manufacturer attribute ID for vibration
XIAOMI_VIBRATION_ATTR = 0x0118  # Decimal 280

# Local-only IAS Zone attribute used to configure the binary sensor reset timer.
VIBRATION_RESET_TIMEOUT = 0xFFF0
DEFAULT_VIBRATION_RESET_TIMEOUT = 70


class AqaraVibrationSensitivity(t.enum8):
    """Aqara vibration sensitivity levels."""

    High = 0x01
    Medium = 0x02
    Low = 0x03


class XiaomiVibrationConfigurationCluster(XiaomiAqaraE1Cluster):
    """Hidden Xiaomi manufacturer cluster used to configure the sensor."""

    class AttributeDefs(XiaomiAqaraE1Cluster.AttributeDefs):
        """Manufacturer-specific configuration attributes."""

        sensitivity_adjustment: Final = ZCLAttributeDef(
            id=0x010E,
            type=AqaraVibrationSensitivity,
            zcl_type=DataTypeId.uint8,
            access="w",
            manufacturer_code=0x115F,
        )


class XiaomiVibrationCluster(XiaomiAqaraE1Cluster):
    """Xiaomi manufacturer cluster on EP2 for vibration detection.

    From Z2M logs: cluster 'manuSpecificLumi', data '{"280":1}' from endpoint 2.
    """

    class AttributeDefs(XiaomiAqaraE1Cluster.AttributeDefs):
        """Attribute definitions."""

        vibration_detected: Final = ZCLAttributeDef(
            id=XIAOMI_VIBRATION_ATTR, type=t.uint8_t, is_manufacturer_specific=True
        )

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == XIAOMI_VIBRATION_ATTR and value == 1:
            self.endpoint.device.motion_bus.listener_event(MOTION_EVENT)
            self.listener_event(ZHA_SEND_EVENT, VIBRATION, {"value": value})


class VibrationMultistateInput(EventableCluster, MultistateInput):
    """Multistate input for triple-tap detection.

    From Z2M logs: cluster 'genMultistateInput', data '{"presentValue":1}'
    from endpoint 2.
    """

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == MultistateInput.AttributeDefs.present_value.id and value == 1:
            # the triple tap is also considered a vibration event, so trigger that as well
            self.endpoint.device.motion_bus.listener_event(MOTION_EVENT)
            self.listener_event(ZHA_SEND_EVENT, TRIPLE_TAP, {"value": value})


class MotionCluster(LocalDataCluster, MotionOnEvent):
    """Exposes vibration as binary_sensor with device_class: vibration.

    Auto-resets to off after the locally configured timeout.
    """

    class AttributeDefs(IasZone.AttributeDefs):
        """Attribute definitions."""

        vibration_reset_timeout: Final = ZCLAttributeDef(
            id=VIBRATION_RESET_TIMEOUT,
            type=t.uint16_t,
            access="rw",
            is_manufacturer_specific=True,
        )

    _CONSTANT_ATTRIBUTES = {ZONE_TYPE: IasZone.ZoneType.Vibration_Movement_Sensor}
    _DEFAULT_VALUES = {
        AttributeDefs.vibration_reset_timeout.id: DEFAULT_VIBRATION_RESET_TIMEOUT
    }
    reset_s = DEFAULT_VIBRATION_RESET_TIMEOUT

    def __init__(self, *args, **kwargs):
        """Initialize the reset timeout from the local attribute cache."""
        super().__init__(*args, **kwargs)
        self.reset_s = int(
            self.get(
                self.AttributeDefs.vibration_reset_timeout.id,
                DEFAULT_VIBRATION_RESET_TIMEOUT,
            )
        )

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == self.AttributeDefs.vibration_reset_timeout.id:
            self.reset_s = int(value)


class VibrationAGL01(CustomZigpyDevice):
    """Aqara Vibration Sensor T1 (DJT12LM) — lumi.vibration.agl01."""

    def __init__(self, *args, **kwargs):
        """Initialize VibrationAGL01."""
        self.motion_bus = Bus()
        super().__init__(*args, **kwargs)


(
    QuirkBuilder(LUMI, "lumi.vibration.agl01")
    .device_class(VibrationAGL01)
    .replaces(BasicCluster)
    .replaces(XiaomiPowerConfiguration)
    .adds(XiaomiVibrationConfigurationCluster)
    .replaces(MotionCluster)
    .replaces(VibrationMultistateInput, endpoint_id=2)
    .removes(IasZone.cluster_id, endpoint_id=2)
    .adds(XiaomiVibrationCluster, endpoint_id=2)
    .number(
        attribute_name=MotionCluster.AttributeDefs.vibration_reset_timeout.name,
        cluster_id=IasZone.cluster_id,
        min_value=1,
        max_value=3600,
        step=1,
        unit=UnitOfTime.SECONDS,
        mode="box",
        device_class=NumberDeviceClass.DURATION,
        translation_key="vibration_reset_timeout",
        fallback_name="Vibration reset timeout",
    )
    .enum(
        attribute_name=XiaomiVibrationConfigurationCluster.AttributeDefs.sensitivity_adjustment.name,
        enum_class=AqaraVibrationSensitivity,
        cluster_id=XiaomiVibrationConfigurationCluster.cluster_id,
        translation_key="sensitivity_adjustment",
        fallback_name="Sensitivity adjustment",
    )
    .device_automation_triggers(
        {
            (VIBRATION, VIBRATION): {
                COMMAND: VIBRATION,
                CLUSTER_ID: XiaomiAqaraE1Cluster.cluster_id,
                ENDPOINT_ID: 2,
            },
            (TRIPLE_TAP, TRIPLE_TAP): {
                COMMAND: TRIPLE_TAP,
                CLUSTER_ID: MultistateInput.cluster_id,
                ENDPOINT_ID: 2,
            },
        }
    )
    .add_to_registry()
)
