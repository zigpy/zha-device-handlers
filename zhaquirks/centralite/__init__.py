"""Centralite module for custom device handlers."""
import logging

from zigpy.quirks import CustomCluster
import zigpy.types as t

_LOGGER = logging.getLogger(__name__)
CENTRALITE = "CentraLite"


class CentraLiteAccelCluster(CustomCluster):
    """Centralite acceleration cluster."""

    cluster_id = 0xFC02
    name = "CentraLite Accelerometer"
    ep_attribute = "accelerometer"
    attributes = {
        0x0000: ("motion_threshold_multiplier", t.uint8_t, True),
        0x0002: ("motion_threshold", t.uint16_t, True),
        0x0010: ("acceleration", t.bitmap8, True),  # acceleration detected
        0x0012: ("x_axis", t.int16s, True),
        0x0013: ("y_axis", t.int16s, True),
        0x0014: ("z_axis", t.int16s, True),
    }
