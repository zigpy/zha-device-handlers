"""EDP WithUs SmartPlug Quirk."""

from zigpy.profiles import zha
from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.edpwithus import MeteringCluster

(
    QuirkBuilder("EDP-WITHUS", "REDY")  # codespell:ignore
    .replaces_endpoint(
        endpoint_id=85,
        profile_id=zha.PROFILE_ID,
        device_type=zha.DeviceType.ON_OFF_PLUG_IN_UNIT,
    )
    .replaces(replacement_cluster_class=MeteringCluster, endpoint_id=85)
    .add_to_registry()
)
