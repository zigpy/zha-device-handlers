"""EDP WithUs SmartPlug Quirk."""

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.smartenergy import Metering


class MeteringCluster(CustomCluster, Metering):
    """EDP WithUs Metering cluster."""

    MULTIPLIER = 0x0301
    DIVISOR = 0x0302
    _CONSTANT_ATTRIBUTES = {MULTIPLIER: 1, DIVISOR: 1000}


(
    QuirkBuilder("EDP-WITHUS", "Smart Plug")
    .replaces_endpoint(
        85, device_type=zha.DeviceType.ON_OFF_PLUG_IN_UNIT
    )  # was MAIN_POWER_OUTLET
    .replaces(MeteringCluster, endpoint_id=85)
    .add_to_registry()
)
