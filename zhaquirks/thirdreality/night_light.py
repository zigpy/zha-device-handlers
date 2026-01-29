"""Third Reality night light zigbee devices."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks import LocalDataCluster
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


(
    QuirkBuilder(THIRD_REALITY, "3RSNL02043Z")
    .replaces(ThirdRealitySpecificCluster, endpoint_id=1)
    .adds(LocalIasZone, endpoint_id=1)
    .add_to_registry()
)
