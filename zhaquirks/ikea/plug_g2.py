"""IKEA INSPELNING and TRETAKT plug quirk."""

from zigpy.quirks.v2 import CustomCluster, QuirkBuilder
import zigpy.types as t
from zigpy.zcl.clusters.general import LevelControl
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.ikea import IKEA


class IkeaSmartPlugCluster(CustomCluster):
    """Ikea Manufacturer Specific SmartPlug cluster."""

    cluster_id: t.uint16_t = (
        0xFC85  # 64645  0xFC85 control smart plug with manufacturer-specific attributes
    )

    class AttributeDefs(BaseAttributeDefs):
        """Cluster attributes."""

        child_lock = ZCLAttributeDef(
            id=0x0000, type=t.Bool, is_manufacturer_specific=True
        )  # deactivates physical switch
        enable_led = ZCLAttributeDef(
            id=0x0001, type=t.Bool, is_manufacturer_specific=True
        )


# remove LevelControl for plugs to not show config options in ZHA
(
    QuirkBuilder(IKEA, "INSPELNING Smart plug")
    .applies_to(IKEA, "TRETAKT Smart plug")
    .removes(LevelControl.cluster_id)
    .replaces(IkeaSmartPlugCluster)
    .switch(
        IkeaSmartPlugCluster.AttributeDefs.child_lock.name,
        IkeaSmartPlugCluster.cluster_id,
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .switch(
        IkeaSmartPlugCluster.AttributeDefs.enable_led.name,
        IkeaSmartPlugCluster.cluster_id,
        off_value=1,
        on_value=0,
        translation_key="disable_led",
        fallback_name="Disable LED",
    )
    .add_to_registry()
)
