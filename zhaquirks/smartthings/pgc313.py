"""SmartThings SmartSense Multi Sensor quirk."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.const import ZONE_TYPE
from zhaquirks.smartthings import SMART_THINGS, SmartThingsIasZone


class IasZoneContactSwitchCluster(SmartThingsIasZone):
    """Custom IasZone cluster."""

    _CONSTANT_ATTRIBUTES = {ZONE_TYPE: IasZone.ZoneType.Contact_Switch}


(
    QuirkBuilder(SMART_THINGS, "PGC313")
    .adds(IasZoneContactSwitchCluster)
    .add_to_registry()
)
