"""Device handler for smartthings moistureV4 sensor."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import PowerConfigurationCluster
from zhaquirks.const import ZONE_TYPE
from zhaquirks.smartthings import SMART_THINGS


class CustomIasZone(CustomCluster, IasZone):
    """Custom IasZone cluster."""

    _CONSTANT_ATTRIBUTES = {ZONE_TYPE: IasZone.ZoneType.Water_Sensor}


(
    QuirkBuilder(SMART_THINGS, "moisturev4")
    .replaces(
        replacement_cluster_class=PowerConfigurationCluster,
        cluster_id=PowerConfigurationCluster.cluster_id,
        endpoint_id=1,
    )
    .replaces(
        replacement_cluster_class=CustomIasZone,
        cluster_id=IasZone.cluster_id,
        endpoint_id=1,
    )
    .add_to_registry()
)
