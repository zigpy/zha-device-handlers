"""Centralite module for custom device handlers."""

from typing import Final

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

CENTRALITE = "CentraLite"


class CentraLiteAccelCluster(CustomCluster):
    """Centralite acceleration cluster."""

    cluster_id = 0xFC02
    name = "CentraLite Accelerometer"
    ep_attribute = "accelerometer"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        motion_threshold_multiplier: Final = ZCLAttributeDef(
            id=0x0000, type=t.uint8_t, is_manufacturer_specific=True
        )
        motion_threshold: Final = ZCLAttributeDef(
            id=0x0002, type=t.uint16_t, is_manufacturer_specific=True
        )
        acceleration: Final = ZCLAttributeDef(
            id=0x0010, type=t.bitmap8, is_manufacturer_specific=True
        )  # acceleration detected
        x_axis: Final = ZCLAttributeDef(
            id=0x0012, type=t.int16s, is_manufacturer_specific=True
        )
        y_axis: Final = ZCLAttributeDef(
            id=0x0013, type=t.int16s, is_manufacturer_specific=True
        )
        z_axis: Final = ZCLAttributeDef(
            id=0x0014, type=t.int16s, is_manufacturer_specific=True
        )
