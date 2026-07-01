"""Third Reality night light zigbee devices."""

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    MultistateInput,
    OnOff,
    Ota,
    Scenes,
)
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.lightlink import LightLink
from zigpy.zcl.clusters.measurement import IlluminanceMeasurement
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks import LocalDataCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.thirdreality import THIRD_REALITY

THIRD_REALITY_CLUSTER_ID = 0xFC00
THIRD_REALITY_MOTION_EVENT_ATTR_ID = 0x0002


class ThirdRealitySpecificCluster(CustomCluster):
    """Manufacturer specific cluster to relay motion event to IAS Zone cluster."""

    cluster_id = THIRD_REALITY_CLUSTER_ID

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        cooldown_time = ZCLAttributeDef(
            id=0x0003,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )
        local_routine_time = ZCLAttributeDef(
            id=0x0004,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )
        lux_threshold = ZCLAttributeDef(
            id=0x0005,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == THIRD_REALITY_MOTION_EVENT_ATTR_ID:
            self.endpoint.ias_zone.update_attribute(
                IasZone.AttributeDefs.zone_status.id, value
            )


class LocalIasZone(LocalDataCluster, IasZone):
    """Local IAS Zone cluster."""

    _CONSTANT_ATTRIBUTES = {
        IasZone.AttributeDefs.zone_type.id: IasZone.ZoneType.Motion_Sensor
    }


class Nightlight(CustomDevice):
    """Custom device for 3RSNL02043Z."""

    signature = {
        MODELS_INFO: [(THIRD_REALITY, "3RSNL02043Z")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    MultistateInput.cluster_id,
                    Color.cluster_id,
                    IlluminanceMeasurement.cluster_id,
                    LightLink.cluster_id,
                    ThirdRealitySpecificCluster.cluster_id,
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
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    MultistateInput.cluster_id,
                    Color.cluster_id,
                    IlluminanceMeasurement.cluster_id,
                    LightLink.cluster_id,
                    LocalIasZone,
                    ThirdRealitySpecificCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            }
        }
    }
