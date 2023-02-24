"""Quirk for LUMI lumi.sensor_smoke.acn03 smoke sensor."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
import zigpy.types as types
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PowerConfiguration
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import Bus, LocalDataCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.xiaomi import DeviceTemperatureCluster, XiaomiAqaraE1Cluster


class OppleCluster(XiaomiAqaraE1Cluster):
    """Opple cluster."""

    ep_attribute = "opple_cluster"
    attributes = {
        0x0126: ("buzzer_manual_mute", types.uint8_t, True),
        0x0127: ("selftest", types.Bool, True),
        0x013A: ("smoke", types.uint8_t, True),
        0x013B: ("smoke_density", types.uint8_t, True),
        0x013C: ("heartbeat_indicator", types.uint8_t, True),
        0x013D: ("buzzer_manual_alarm", types.uint8_t, True),
        0x013E: ("buzzer", types.uint32_t, True),
        0x014B: ("linkage_alarm", types.uint8_t, True),
    }


class LocalIasZone(LocalDataCluster, IasZone):
    """Local IAS Zone cluster."""

    _CONSTANT_ATTRIBUTES = {
        IasZone.attributes_by_name["zone_type"].id: IasZone.ZoneType.Fire_Sensor
    }


class LumiSensorSmokeAcn03(CustomDevice):
    """lumi.sensor_smoke.acn03 smoke sensor."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.battery_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [("LUMI", "lumi.sensor_smoke.acn03")],
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
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    LocalIasZone,
                    DeviceTemperatureCluster,
                    OppleCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            }
        }
    }
