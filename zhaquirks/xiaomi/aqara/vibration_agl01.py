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
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks import Bus, EventableCluster, LocalDataCluster, MotionOnEvent
from zhaquirks.builder import QuirkBuilder
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

    Auto-resets to off after 70 seconds.
    """

    _CONSTANT_ATTRIBUTES = {ZONE_TYPE: IasZone.ZoneType.Vibration_Movement_Sensor}
    reset_s = 70


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
    .adds(XiaomiAqaraE1Cluster)
    .replaces(MotionCluster)
    .replaces(VibrationMultistateInput, endpoint_id=2)
    .replaces(
        XiaomiVibrationCluster,
        cluster_id=IasZone.cluster_id,
        endpoint_id=2,
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
