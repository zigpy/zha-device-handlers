"""Sonoff ZBMicro - Zigbee USB repeater plug."""

import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster


class SonoffCluster(CustomCluster):
    """Custom Sonoff cluster."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        # Unlike the ZBMINIR2, the ZBMicro answers UNSUPPORTED_ATTRIBUTE
        # for 0x0012 without the manufacturer code
        turbo_mode = ZCLAttributeDef(
            id=0x0012,
            type=t.int16s,
            manufacturer_code=0x1286,
        )


(
    QuirkBuilder("SONOFF", "ZBMicro")
    .replaces(SonoffCluster)
    .switch(
        attribute_name=SonoffCluster.AttributeDefs.turbo_mode.name,
        cluster_id=SonoffCluster.cluster_id,
        off_value=9,
        on_value=20,
        translation_key="turbo_mode",
        fallback_name="Turbo mode",
    )
    .add_to_registry()
)
