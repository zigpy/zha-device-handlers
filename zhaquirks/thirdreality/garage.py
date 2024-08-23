"""Third Reality garage sensor devices."""
from zigpy.profiles import zha
from typing import Final
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Ota, PowerConfiguration
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import CustomCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.thirdreality import THIRD_REALITY
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

THIRD_REALITY_GARAGE_CLUSTER_ID = 0xFF01
DELAY_OPEN_ATTR_ID = 0x0000
ZCL_CABRATION_ATTR_ID = 0x0003

class ControlMode(t.uint16_t):
    """Reset mode for not clear and clear."""
	

class ThirdRealityGarageCluster(CustomCluster):
	"""ThirdReality Acceleration Cluster."""
	cluster_id = THIRD_REALITY_GARAGE_CLUSTER_ID

	class AttributeDefs(BaseAttributeDefs):
		delay_open: Final = ZCLAttributeDef(
		id=DELAY_OPEN_ATTR_ID,
		type=ControlMode,
		is_manufacturer_specific=True
		)
		zcl_cabration: Final = ZCLAttributeDef(
		id=ZCL_CABRATION_ATTR_ID,
		type=t.uint8_t,
		is_manufacturer_specific=True
		)
		
		
    


class Garage(CustomDevice):
    """ThirdReality garage device."""

    signature = {
        MODELS_INFO: [(THIRD_REALITY, "3RDTS01056Z")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    IasZone.cluster_id,
                    ThirdRealityGarageCluster.cluster_id,
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
                    IasZone.cluster_id,
                    ThirdRealityGarageCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            }
        },
    }
