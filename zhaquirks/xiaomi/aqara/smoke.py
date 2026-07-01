"""Quirk for LUMI lumi.sensor_smoke.acn03 smoke sensor."""

from typing import Any

from zigpy import types
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PowerConfiguration
from zigpy.zcl.clusters.security import IasZone
from zigpy.zdo.types import NodeDescriptor

from zhaquirks import LocalDataCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    NODE_DESCRIPTOR,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    ZONE_STATUS,
)
from zhaquirks.xiaomi import LUMI, XiaomiAqaraE1Cluster, XiaomiPowerConfiguration

BUZZER_MANUAL_MUTE = 0x0126
SELF_TEST = 0x0127
SMOKE = 0x013A
SMOKE_DENSITY = 0x013B
HEARTBEAT_INDICATOR = 0x013C
BUZZER_MANUAL_ALARM = 0x013D
BUZZER = 0x013E
LINKAGE_ALARM = 0x014B
LINKAGE_ALARM_STATE = 0x014C
SMOKE_DENSITY_DBM = 0x1403  # fake attribute for smoke density in dB/m

SMOKE_DENSITY_DBM_MAP = {
    0: 0,
    1: 0.085,
    2: 0.088,
    3: 0.093,
    4: 0.095,
    5: 0.100,
    6: 0.105,
    7: 0.110,
    8: 0.115,
    9: 0.120,
    10: 0.125,
}


class OppleCluster(XiaomiAqaraE1Cluster):
    """Opple cluster."""

    attributes = {
        BUZZER_MANUAL_MUTE: ("buzzer_manual_mute", types.uint8_t, True),
        SELF_TEST: ("self_test", types.Bool, True),
        SMOKE: ("smoke", types.uint8_t, True),
        SMOKE_DENSITY: ("smoke_density", types.uint8_t, True),
        HEARTBEAT_INDICATOR: ("heartbeat_indicator", types.uint8_t, True),
        BUZZER_MANUAL_ALARM: ("buzzer_manual_alarm", types.uint8_t, True),
        BUZZER: ("buzzer", types.uint32_t, True),
        LINKAGE_ALARM: ("linkage_alarm", types.uint8_t, True),
        LINKAGE_ALARM_STATE: ("linkage_alarm_state", types.uint8_t, True),
        SMOKE_DENSITY_DBM: ("smoke_density_dbm", types.Single, True),
    }

    def _update_attribute(self, attrid: int, value: Any) -> None:
        """Pass attribute update to another cluster if necessary."""
        super()._update_attribute(attrid, value)
        if attrid == SMOKE:
            self.endpoint.ias_zone.update_attribute(ZONE_STATUS, value)
        elif attrid == SMOKE_DENSITY:
            self.update_attribute(SMOKE_DENSITY_DBM, SMOKE_DENSITY_DBM_MAP[value])


class LocalIasZone(LocalDataCluster, IasZone):
    """Local IAS Zone cluster."""

    _CONSTANT_ATTRIBUTES = {
        IasZone.attributes_by_name["zone_type"].id: IasZone.ZoneType.Fire_Sensor
    }


class LumiSensorSmokeAcn03(CustomDevice):
    """lumi.sensor_smoke.acn03 smoke sensor."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.sensor_smoke.acn03")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    IasZone.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            }
        },
    }

    replacement = {
        NODE_DESCRIPTOR: NodeDescriptor(
            0x02, 0x40, 0x80, 0x115F, 0x7F, 0x0064, 0x2C00, 0x0064, 0x00
        ),
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    XiaomiPowerConfiguration,
                    Identify.cluster_id,
                    LocalIasZone,
                    OppleCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            }
        },
    }
