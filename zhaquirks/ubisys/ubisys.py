from zigpy.quirks.v2 import CustomCluster, CustomDeviceV2, QuirkBuilder
import zigpy.types as t
from zigpy.zcl import ClusterType
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class UbisysDevice(CustomDeviceV2):
    """Ubisys device class"""


class UbisysManufacturerSpecificCluster(CustomCluster):
    """Ubisys manufacturer specific cluster"""

    cluster_id = 0xFC00
    name = "Ubisys Manufacturer Specific"
    ep_attribute = "ubisys_manufacturer_specific"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        input_configurations = ZCLAttributeDef(
            id=0x0000, type=t.LVBytes, is_manufacturer_specific=True
        )
        input_actions = ZCLAttributeDef(
            id=0x0001, type=t.LVBytes, is_manufacturer_specific=True
        )


(
    QuirkBuilder("ubisys", "S1 (5501)")
    .also_applies_to("ubisys", "S2 (5502)")
    .device_class(UbisysDevice)
    .replaces(UbisysManufacturerSpecificCluster, 0xFC00, ClusterType.Server, 232)
    .add_to_registry()
)
