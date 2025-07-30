"""Texas Instruments Z-Stack router device."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.foundation import ZCLAttributeDef


class BasicCluster(CustomCluster, Basic):
    """Texas Instruments Basic cluster."""

    class AttributeDefs(Basic.AttributeDefs):
        """Attribute definitions."""

        transmit_power: Final = ZCLAttributeDef(
            id=0x1337, type=t.int8s, is_manufacturer_specific=True
        )


(
    QuirkBuilder("TexasInstruments", "ti.router")
    .replaces(
        replacement_cluster_class=BasicCluster,
        cluster_id=Basic.cluster_id,
        endpoint_id=8,
    )
    .replaces(
        replacement_cluster_class=BasicCluster,
        cluster_id=Basic.cluster_id,
        endpoint_id=8,
        cluster_type="output",
    )
    .add_to_registry()
)
