"""Third Reality 60G radar devices."""

from typing import Final

import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import (
    CONCENTRATION_PARTS_PER_BILLION,
    NumberDeviceClass,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
)
from zhaquirks.clusters import CustomCluster


class ThirdRealityRadarCluster(CustomCluster):
    """Third Reality's 60G radar private cluster."""

    cluster_id = 0x042E

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        # measure the value of voc
        volatile_organic_compounds: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.Single,
            is_manufacturer_specific=True,
        )

        tvoc_sensor_calibration: Final = ZCLAttributeDef(
            id=0xF001,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )

        sensor_sensitivity: Final = ZCLAttributeDef(
            id=0xF002,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )

        air_threshold: Final = ZCLAttributeDef(
            id=0xF003,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder("Third Reality, Inc", "3RPL01084Z")
    .replaces(ThirdRealityRadarCluster)
    .sensor(
        attribute_name=ThirdRealityRadarCluster.AttributeDefs.volatile_organic_compounds.name,
        cluster_id=ThirdRealityRadarCluster.cluster_id,
        device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS,
        state_class=SensorStateClass.MEASUREMENT,
        unit=CONCENTRATION_PARTS_PER_BILLION,
        translation_key="total_volatile_organic_compounds",
        fallback_name="Total volatile organic compounds",
    )
    .write_attr_button(
        cluster_id=ThirdRealityRadarCluster.cluster_id,
        attribute_name=ThirdRealityRadarCluster.AttributeDefs.tvoc_sensor_calibration.name,
        attribute_value=0x01,
        translation_key="calibrate_tvoc_sensor",
        fallback_name="Calibrate TVOC sensor",
    )
    .number(
        attribute_name=ThirdRealityRadarCluster.AttributeDefs.sensor_sensitivity.name,
        min_value=1,
        max_value=6,
        step=1,
        cluster_id=ThirdRealityRadarCluster.cluster_id,
        translation_key="presence_sensor_sensitivity",
        fallback_name="Presence sensor sensitivity",
    )
    .number(
        attribute_name=ThirdRealityRadarCluster.AttributeDefs.air_threshold.name,
        cluster_id=ThirdRealityRadarCluster.cluster_id,
        min_value=3000,
        max_value=50000,
        step=1,
        device_class=NumberDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS,
        unit=CONCENTRATION_PARTS_PER_BILLION,
        translation_key="air_threshold",
        fallback_name="Air threshold",
    )
    .add_to_registry()
)
