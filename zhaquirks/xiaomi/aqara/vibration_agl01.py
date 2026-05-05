"""Aqara Vibration Sensor T1 (DJT12LM) — lumi.vibration.agl01.

Based on nachtaap's quirk from zigpy/zha-device-handlers#4137, enhanced with
MotionCluster for binary_sensor entity.

Data paths observed:
- IAS Zone attr 0x002D on EP2→dst EP1: value=1 vibration, value=2 triple-tap
- manuSpecificLumi attr 0x0118 (280) on EP2: value=1 vibration
- MultistateInput presentValue on EP2: value=1 triple-tap

Author: @mengwong. Originally shared as GitHub Gist https://gist.github.com/mengwong/b3ca949249405f99f03dce270d3029f5
in issue https://github.com/zigpy/zha-device-handlers/issues/4137#issuecomment-4205558840
"""

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    MultistateInput,
    Ota,
    PowerConfiguration,
)
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks import Bus, EventableCluster, LocalDataCluster, MotionOnEvent
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    MOTION_EVENT,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    ZHA_SEND_EVENT,
    ZONE_TYPE,
)
from zhaquirks.xiaomi import (
    LUMI,
    BasicCluster,
    XiaomiAqaraE1Cluster,
    XiaomiCustomDevice,
    XiaomiPowerConfiguration,
)

# Event types
VIBRATION = "vibration"
TRIPLE_TAP = "triple_tap"

# Xiaomi manufacturer attribute for vibration
XIAOMI_VIBRATION_ATTR = 0x0118  # Decimal 280

class XiaomiVibrationCluster(XiaomiAqaraE1Cluster):
    """Xiaomi manufacturer cluster on EP2 for vibration detection.

    From Z2M logs: cluster 'manuSpecificLumi', data '{"280":1}' from endpoint 2.
    """

    attributes = XiaomiAqaraE1Cluster.attributes.copy()
    attributes.update(
        {
            XIAOMI_VIBRATION_ATTR: ("vibration_detected", t.uint8_t, True),
        }
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


class VibrationAGL01(XiaomiCustomDevice):
    """Aqara Vibration Sensor T1 (DJT12LM) — lumi.vibration.agl01."""

    def __init__(self, *args, **kwargs):
        """Initialize VibrationAGL01."""
        self.motion_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [(LUMI, "lumi.vibration.agl01")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x0402,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0x0000
                    PowerConfiguration.cluster_id,  # 0x0001
                    Identify.cluster_id,  # 0x0003
                    IasZone.cluster_id,  # 0x0500
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,  # 0x0003
                    Ota.cluster_id,  # 0x0019
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x0402,
                INPUT_CLUSTERS: [
                    MultistateInput.cluster_id,  # 0x0012
                    IasZone.cluster_id,  # 0x0500
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x0402,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    XiaomiPowerConfiguration,
                    XiaomiAqaraE1Cluster,
                    Identify.cluster_id,
                    MotionCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x0402,
                INPUT_CLUSTERS: [
                    VibrationMultistateInput,
                    XiaomiVibrationCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    device_automation_triggers = {
        (VIBRATION, VIBRATION): {"type": VIBRATION, "subtype": VIBRATION},
        (TRIPLE_TAP, TRIPLE_TAP): {"type": TRIPLE_TAP, "subtype": TRIPLE_TAP},
    }
