"""Device handler for smartthings moistureV4 sensor."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import PowerConfigurationCluster
from zhaquirks.smartthings import SMART_THINGS


class CustomIasZone(CustomCluster, IasZone):
    """Custom IasZone cluster."""

    _CONSTANT_ATTRIBUTES = {
        IasZone.AttributeDefs.zone_type.id: IasZone.ZoneType.Water_Sensor,
    }


(
    QuirkBuilder(SMART_THINGS, "moisturev4")
    .replaces(PowerConfigurationCluster, endpoint_id=1)
    .replaces(CustomIasZone, endpoint_id=1)
    .add_to_registry()
)
