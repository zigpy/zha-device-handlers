"""Module for Candeo quirks implementations."""

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.foundation import DataTypeId, ZCLAttributeDef

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
            access="rw",
            is_manufacturer_specific=True,
        )
