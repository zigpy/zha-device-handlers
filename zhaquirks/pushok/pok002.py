"""Quirk for PushOk POK002/POK007 soil moisture sensor.

Maps MultistateValue (0x0014) presentValue → max_moisture number entity
"""

from zigpy.zcl.clusters.general import MultistateValue
from zigpy.zcl.clusters.measurement import RelativeHumidity

from zhaquirks.builder import PERCENTAGE, EntityType, QuirkBuilder

(
    QuirkBuilder("PushOk Hardware", "POK002")
    .applies_to("PushOk Hardware", "POK007")
    .number(
        attribute_name=MultistateValue.AttributeDefs.present_value.name,
        unique_id_suffix="max_moisture",
        cluster_id=MultistateValue.cluster_id,
        endpoint_id=1,
        min_value=1,
        max_value=100,
        step=1,
        unit=PERCENTAGE,
        entity_type=EntityType.CONFIG,
        fallback_name="Max moisture",
        translation_key="max_moisture",
    )
    .change_entity_metadata(
        endpoint_id=1,
        cluster_id=RelativeHumidity.cluster_id,
        new_translation_key="soil_moisture",
        new_fallback_name="Soil moisture",
    )
    .add_to_registry()
)
