"""Third Reality night light zigbee devices."""
from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
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
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.lightlink import LightLink
from zigpy.zcl.clusters.measurement import (
    IlluminanceMeasurement,
)

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.thirdreality import THIRD_REALITY
from zhaquirks import LocalDataCluster

ThirdReality_Specific_CLUSTER_ID = 0xFC00

class ThirdRealitySpecificCluster(CustomCluster):
    """privatecluster, only used to relay ias zone information to ias zone Cluster."""

    cluster_id = ThirdReality_Specific_CLUSTER_ID

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        self.endpoint.ias_zone.update_attribute(IasZone.AttributeDefs.zone_status.id, value)

class LocalIasZone(LocalDataCluster, IasZone):
    """Local IAS Zone cluster."""

    _CONSTANT_ATTRIBUTES = {
        IasZone.attributes_by_name["zone_type"].id: IasZone.ZoneType.Motion_Sensor
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
