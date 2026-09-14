"""Device handler for Shelly BLU Distance ZB."""

from __future__ import annotations

from zigpy import types
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import (
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfLength,
)
from zhaquirks.clusters import CustomCluster
from zhaquirks.shelly import SHELLY_MANUFACTURER_CODE


class ShellyDistanceCluster(CustomCluster):
    """Shelly manufacturer-specific distance/occupancy configuration cluster."""

    cluster_id = 0xFC22
    name = "Shelly Distance Config"
    ep_attribute = "shelly_distance_config"

    class AttributeDefs(BaseAttributeDefs):
        """Distance cluster attribute definitions."""

        distance = ZCLAttributeDef(
            id=0x0000,
            type=types.uint16_t,
            access="rp",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        occupied_threshold = ZCLAttributeDef(
            id=0x0001,
            type=types.uint16_t,
            access="rw",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )
        hysteresis = ZCLAttributeDef(
            id=0x0002,
            type=types.uint16_t,
            access="rw",
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )


(
    QuirkBuilder("Shelly", "BLU Distance")
    .replaces(ShellyDistanceCluster)
    .sensor(
        attribute_name=ShellyDistanceCluster.AttributeDefs.distance.name,
        cluster_id=ShellyDistanceCluster.cluster_id,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfLength.MILLIMETERS,
        reporting_config=ReportingConfig(
            min_interval=15, max_interval=300, reportable_change=1
        ),
        translation_key="target_distance",
        fallback_name="Target distance",
    )
    .add_to_registry()
)
