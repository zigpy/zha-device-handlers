"""Module for Schneider Electric devices quirks."""
import logging

from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.closures import WindowCovering

from zhaquirks import Bus, EventableCluster, LocalDataCluster

_LOGGER = logging.getLogger(__name__)

SE = "Schneider Electric"

class SEManufCluster(CustomCluster):
    """Schneider Electric manufacturer specific cluster."""

    name = "Schneider Electric Manufacturer Specicific"
    ep_attribute = "schneider_electric_manufacturer"


class SEManufSwitchCluster(SEManufCluster):
    name = "Schneider Electric Manufacturer Specicific"
    cluster_id = 0xFF17


class SEWindowCoverControl(CustomCluster, WindowCovering):
    """Manufacturer Specific Cluster of Device cover."""

    attributes = WindowCovering.attributes.copy()

    attributes.update({0xE000: ("lift_duration", t.uint16_t)})

    # def __init__(self, *args, **kwargs):
    #     """Initialize instance."""
    #     super().__init__(*args, **kwargs)
    #     self.endpoint.device.cover_bus.add_listener(self)

    # def cover_event(self, attribute, value):
    #     """Event listener for cover events."""
    #     if attribute == "lift_duration":
    #         lift_duration_attr = self._attr_cache.get("lift_duration") == 1
    #     self._update_attribute(attribute, value)
    #     _LOGGER.debug(
    #         "%s Schneider Attribute Cache : [%s]",
    #         self.endpoint.device.ieee,
    #         self._attr_cache,
    #     )
