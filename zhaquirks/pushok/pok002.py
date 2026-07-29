"""Quirk for PushOk POK002/POK007 soil moisture sensor.

Maps MultistateValue (0x0014) presentValue → max_moisture number entity
"""

from zigpy.zcl.clusters.general import MultistateValue

from zhaquirks.builder import EntityType, QuirkBuilder

(
    QuirkBuilder("PushOk Hardware", "POK002")
    .also_applies_to("PushOk Hardware", "POK007")
    .number(
        attribute_name="present_value",
        unique_id_suffix="max_moisture",
        cluster_id=MultistateValue.cluster_id,
        endpoint_id=1,
        min_value=1,
        max_value=100,
        step=1,
        unit="%",
        entity_type=EntityType.CONFIG,
        fallback_name="Max moisture",
        translation_key="max_moisture",
    )
    .add_to_registry()
)
