"""SmartThings SmartSense Multi Sensor quirk."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.security import ZoneType

from zhaquirks.smartthings import SMART_THINGS, SmartThingsIasZone


class IasZoneContactSwitchCluster(SmartThingsIasZone):
    """Custom IasZone cluster."""

    _CONSTANT_ATTRIBUTES = {
        SmartThingsIasZone.AttributeDefs.zone_type.id: ZoneType.Contact_Switch
    }


(
    QuirkBuilder(SMART_THINGS, "PGC313")
    .adds(IasZoneContactSwitchCluster, endpoint_id=1)
    .removes_endpoint(2)  # TODO: is this necessary?
    .add_to_registry()
)
