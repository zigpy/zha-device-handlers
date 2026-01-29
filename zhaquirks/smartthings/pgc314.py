"""SmartThings SmartSense Motion quirk."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.security import ZoneType

from zhaquirks.smartthings import SMART_THINGS, SmartThingsIasZone


class IasZoneMotionCluster(SmartThingsIasZone):
    """Custom IasZone cluster."""

    _CONSTANT_ATTRIBUTES = {
        SmartThingsIasZone.AttributeDefs.zone_type.id: ZoneType.Motion_Sensor
    }


(
    QuirkBuilder(SMART_THINGS, "PGC314")
    .adds(IasZoneMotionCluster, endpoint_id=1)
    .add_to_registry()
)
