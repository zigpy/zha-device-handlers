"""Linkind sensors."""
from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic


class LinkindBasicCluster(CustomCluster, Basic):
    """Linkind Basic cluster."""

    attributes = Basic.attributes.copy()
    attributes.update({0x0400A: ("linkind", t.uint8_t, True)})
