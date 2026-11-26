"""Sonoff SNZB-02B - Zigbee temperature humidity sensor (AirGuard TH Lite)."""

import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import (
    PERCENTAGE,
    NumberDeviceClass,
    QuirkBuilder,
    UnitOfTemperature,
)
from zhaquirks.clusters import CustomCluster


class CustomSonoffCluster(CustomCluster):
    """Sonoff custom cluster."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        temperature_offset = ZCLAttributeDef(
            id=0x2003,
            type=t.int16s,
            manufacturer_code=None,
        )

        humidity_offset = ZCLAttributeDef(
            id=0x2004,
            type=t.int16s,
            manufacturer_code=None,
        )


(
    QuirkBuilder("SONOFF", "SNZB-02B")
    .replaces(CustomSonoffCluster)
    .number(
        CustomSonoffCluster.AttributeDefs.temperature_offset.name,
        CustomSonoffCluster.cluster_id,
        min_value=-50,
        max_value=50,
        step=0.1,
        device_class=NumberDeviceClass.TEMPERATURE_DELTA,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="temperature_offset",
        fallback_name="Temperature offset",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.humidity_offset.name,
        CustomSonoffCluster.cluster_id,
        min_value=-50,
        max_value=50,
        step=0.1,
        device_class=NumberDeviceClass.HUMIDITY,
        unit=PERCENTAGE,
        multiplier=0.01,
        translation_key="humidity_offset",
        fallback_name="Humidity offset",
    )
    .add_to_registry()
)
