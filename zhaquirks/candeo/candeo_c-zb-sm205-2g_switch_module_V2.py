"""Candeo C-ZB-SM205-2G Switch Module."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.foundation import ZCLAttributeDef, DataTypeId

CANDEO = "Candeo"

class CandeoSwitchType(t.enum8):
    """Candeo Switch Type."""

    Momentary = 0x00
    Toggle = 0x01

class CandeoBasicCluster(Basic, CustomCluster):
    """Candeo Basic Cluster."""

    class AttributeDefs(Basic.AttributeDefs):
        """Attribute Definitions."""

        external_switch_type = ZCLAttributeDef(
            id=0x8803,
            type=CandeoSwitchType,
            zcl_type=DataTypeId.uint8,
            is_manufacturer_specific=True,
        )

    attr_config = {AttributeDefs.external_switch_type.id: CandeoSwitchType.Toggle}

    async def apply_custom_configuration(self, *args, **kwargs):
        """Apply Custom Configuration."""
        await self.write_attributes(self.attr_config, manufacturer=0x1224)

(
    QuirkBuilder(CANDEO, "C-ZB-SM205-2G")
    .replaces(CandeoBasicCluster, endpoint_id=11)
    .enum(
        attribute_name=CandeoBasicCluster.AttributeDefs.external_switch_type.name,
        enum_class=CandeoSwitchType,
        cluster_id=CandeoBasicCluster.cluster_id,
        endpoint_id=11,
        initially_disabled=False,
        translation_key="external_switch_type",
        fallback_name="External Switch Type",
    )
    .add_to_registry()
)
