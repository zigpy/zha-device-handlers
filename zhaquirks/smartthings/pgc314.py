"""SmartThings SmartSense Motion quirk."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.smartthings import SMART_THINGS, SmartThingsIasZone

SMARTSENSE_MOTION_DEVICE_TYPE = 0x013A  # decimal = 314


class IasZoneMotionCluster(SmartThingsIasZone):
    """Custom IasZone cluster."""

    ZONE_TYPE = 0x0001
    MOTION_TYPE = 0x000D
    _CONSTANT_ATTRIBUTES = {ZONE_TYPE: MOTION_TYPE}


(
    QuirkBuilder(SMART_THINGS, "PGC314")
    .adds(IasZoneMotionCluster, endpoint_id=1)
    .removes_endpoint(endpoint_id=2)
    .add_to_registry()
)
