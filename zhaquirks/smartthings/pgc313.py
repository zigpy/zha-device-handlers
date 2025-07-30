"""SmartThings SmartSense Multi Sensor quirk."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.const import ZONE_TYPE
from zhaquirks.smartthings import SMART_THINGS, SmartThingsIasZone

SMARTSENSE_MULTI_DEVICE_TYPE = 0x0139  # decimal = 313


class IasZoneContactSwitchCluster(SmartThingsIasZone):
    """Custom IasZone cluster."""

    _CONSTANT_ATTRIBUTES = {ZONE_TYPE: IasZone.ZoneType.Contact_Switch}


(
    QuirkBuilder(SMART_THINGS, "PGC313")
    .adds(IasZoneContactSwitchCluster, endpoint_id=1)
    .removes_endpoint(endpoint_id=2)
    .add_to_registry()
)
