"""Third Reality night light zigbee devices."""

import zigpy.types as t
from zigpy.zcl.clusters.general import MultistateInput
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks import LocalDataCluster
from zhaquirks.builder import (
    LIGHT_LUX,
    NumberDeviceClass,
    QuirkBuilder,
    ReportingConfig,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster
from zhaquirks.thirdreality import THIRD_REALITY

THIRD_REALITY_CLUSTER_ID = 0xFC00
THIRD_REALITY_MOTION_EVENT_ATTR_ID = 0x0002

# The local routine (motion turns the light on when it is dark) is toggled with
# the pinhole button and shows up in present_value of the MultistateInput cluster
LOCAL_ROUTINE_ON = 86
LOCAL_ROUTINE_OFF = 87


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
    .replaces(ThirdRealitySpecificCluster)
    .adds(LocalIasZone)
    .switch(
        attribute_name=MultistateInput.AttributeDefs.present_value.name,
        cluster_id=MultistateInput.cluster_id,
        on_value=LOCAL_ROUTINE_ON,
        off_value=LOCAL_ROUTINE_OFF,
        reporting_config=ReportingConfig(
            min_interval=0, max_interval=900, reportable_change=1
        ),
        translation_key="local_routine",
        fallback_name="Local routine",
    )
    .number(
        attribute_name=ThirdRealitySpecificCluster.AttributeDefs.local_routine_time.name,
        cluster_id=ThirdRealitySpecificCluster.cluster_id,
        min_value=10,
        max_value=3600,
        step=1,
        unit=UnitOfTime.SECONDS,
        translation_key="local_routine_time",
        fallback_name="Local routine time",
    )
    .number(
        attribute_name=ThirdRealitySpecificCluster.AttributeDefs.lux_threshold.name,
        cluster_id=ThirdRealitySpecificCluster.cluster_id,
        min_value=0,
        max_value=1000,
        step=1,
        unit=LIGHT_LUX,
        device_class=NumberDeviceClass.ILLUMINANCE,
        translation_key="illuminance_threshold",
        fallback_name="Illuminance threshold",
    )
    .add_to_registry()
)
