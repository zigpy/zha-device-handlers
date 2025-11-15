"""EDP WithUs SmartPlug Quirk."""

from zigpy.profiles import zha
from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.edpwithus import MeteringCluster

(
    QuirkBuilder("EDP-WITHUS", "Smart Plug")
    .replaces_endpoint(85, device_type=zha.DeviceType.ON_OFF_PLUG_IN_UNIT)
    .replaces(MeteringCluster, endpoint_id=85)
    .add_to_registry()
)
