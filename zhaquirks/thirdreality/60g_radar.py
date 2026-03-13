"""Third Reality 60g radar devices."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder, SensorDeviceClass, SensorStateClass
from zigpy.quirks.v2.homeassistant import CONCENTRATION_PARTS_PER_BILLION
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class ThirdRealityRadarCluster(CustomCluster):
    """Third Reality's 60g radar private cluster."""

    cluster_id = 0x042E

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        # measure the value of voc
        volatile_organic_compounds: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.Single,
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder("Third Reality, Inc", "3RPL01084Z")
    .replaces(ThirdRealityRadarCluster)
    .sensor(
        endpoint_id=1,
        attribute_name=ThirdRealityRadarCluster.AttributeDefs.volatile_organic_compounds.name,
        cluster_id=ThirdRealityRadarCluster.cluster_id,
        device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS,
        state_class=SensorStateClass.MEASUREMENT,
        unit=CONCENTRATION_PARTS_PER_BILLION,
        fallback_name="Volatile organic compounds parts",
    )
    .add_to_registry()
)
