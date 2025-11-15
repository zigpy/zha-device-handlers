"""SmartThings SmartSense Motion quirk."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.smartthings import SMART_THINGS, SmartThingsIasZone


class IasZoneMotionCluster(SmartThingsIasZone):
    """Custom IasZone cluster."""

    ZONE_TYPE = 0x0001
    MOTION_TYPE = 0x000D
    _CONSTANT_ATTRIBUTES = {ZONE_TYPE: MOTION_TYPE}


(QuirkBuilder(SMART_THINGS, "PGC314").adds(IasZoneMotionCluster).add_to_registry())
