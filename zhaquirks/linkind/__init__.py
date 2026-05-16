"""Linkind sensors."""

from typing import Final

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.foundation import ZCLAttributeDef


class LinkindBasicCluster(CustomCluster, Basic):
    """Linkind Basic cluster."""

    class AttributeDefs(Basic.AttributeDefs):
        """Attribute definitions."""

        linkind: Final = ZCLAttributeDef(
            id=0x0400A, type=t.uint8_t, is_manufacturer_specific=True
        )
