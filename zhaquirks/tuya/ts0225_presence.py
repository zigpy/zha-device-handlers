"""TS0225 presence sensor."""

from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
from zigpy.quirks import CustomCluster
from zhaquirks.tuya.builder import TuyaQuirkBuilder

from homeassistant.const import UnitOfLength, UnitOfTime

from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

import zigpy.types as t

class TS0225Cluster(CustomCluster):
    cluster_id = 0xE002
    class AttributeDefs(BaseAttributeDefs):
        presence_keep_time = ZCLAttributeDef(
            id = 0xE001,
            type = t.uint16_t,
            is_manufacturer_specific=False
        )
        motion_detection_sensitivity = ZCLAttributeDef(
            id = 0xE004,
            type = t.uint8_t,
            access="rw",
            is_manufacturer_specific=False
        )
        static_detection_sensitivity = ZCLAttributeDef(
            id = 0xE005,
            type = t.uint8_t,
            access="rw",
            is_manufacturer_specific=False
        )
        target_distance = ZCLAttributeDef(
            id = 0xE00A,
            type = t.uint16_t,
            is_manufacturer_specific=False
        )
        motion_detection_distance = ZCLAttributeDef(
            id = 0xE00B,
            type = t.uint16_t,
            access="rw",
            is_manufacturer_specific=False
        )

(
    TuyaQuirkBuilder("_TZ3218_awarhusb", "TS0225")
    .replaces(TS0225Cluster)
    .sensor(
        TS0225Cluster.AttributeDefs.target_distance.name,
        TS0225Cluster.cluster_id,
        unit=UnitOfLength.CENTIMETERS,
        fallback_name="Target distance",
        translation_key="target_distance"
    )
    .sensor(
        TS0225Cluster.AttributeDefs.presence_keep_time.name,
        TS0225Cluster.cluster_id,
        unit=UnitOfTime.MINUTES,
        fallback_name="Presence keep time",
        translation_key="presence_keep_time"
    )
    .number(
        TS0225Cluster.AttributeDefs.motion_detection_sensitivity.name,
        TS0225Cluster.cluster_id,
        min_value=0,
        max_value=5,
        step=1,
        fallback_name="Motion detection sensitivity",
        translation_key="motion_detection_sensitivity"
    )
    .number(
        TS0225Cluster.AttributeDefs.static_detection_sensitivity.name,
        TS0225Cluster.cluster_id,
        min_value=0,
        max_value=5,
        step=1,
        fallback_name="Static detection sensitivity",
        translation_key="static_detection_sensitivity"
    )
    .number(
        TS0225Cluster.AttributeDefs.motion_detection_distance.name,
        TS0225Cluster.cluster_id,
        min_value=75,
        max_value=600,
        unit=UnitOfLength.CENTIMETERS,
        device_class=NumberDeviceClass.DISTANCE,
        step=75,
        fallback_name="Motion detection distance",
        translation_key="motion_detection_distance"
    )
    .tuya_number(
        dp_id=101,
        attribute_name="fading_time",
        type=t.uint16_t,
        min_value=0,
        max_value=10000,
        step=1,
        unit=UnitOfTime.SECONDS,
        translation_key="fading_time",
        fallback_name="fading_time",
    )
    .skip_configuration()
    .add_to_registry()
)
