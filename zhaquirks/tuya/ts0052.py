"""Tuya TS0052 2-channel dimmer quirk."""

import zigpy.types as t
from zigpy.zcl import foundation

from zhaquirks.builder import EntityType, QuirkBuilder
from zhaquirks.clusters import CustomCluster


class SwitchType(t.enum8):
    """External wall switch type."""

    Toggle = 0
    State = 1
    Momentary = 2


class TuyaSwitchTypeCluster(CustomCluster):
    """Tuya cluster exposing the external switch type setting."""

    cluster_id = 0xE001

    class AttributeDefs(CustomCluster.AttributeDefs):
        """Attribute definitions."""

        switch_type = foundation.ZCLAttributeDef(
            id=0xD030,
            type=SwitchType,
            access="rw",
            is_manufacturer_specific=False,
        )


(
    QuirkBuilder("_TZ3000_zjtxnoft", "TS0052")
    .replaces(TuyaSwitchTypeCluster, endpoint_id=1)
    .replaces(TuyaSwitchTypeCluster, endpoint_id=2)
    .enum(
        attribute_name=TuyaSwitchTypeCluster.AttributeDefs.switch_type.name,
        enum_class=SwitchType,
        cluster_id=TuyaSwitchTypeCluster.cluster_id,
        endpoint_id=1,
        entity_type=EntityType.CONFIG,
        translation_key="switch_type",
        fallback_name="Switch type",
    )
    .add_to_registry()
)
