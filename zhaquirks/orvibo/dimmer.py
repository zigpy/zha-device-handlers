"""ORVIBO dimmers."""

from zigpy.profiles import zha
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.lighting import Color

from zhaquirks.orvibo import ORVIBO

(
    QuirkBuilder(ORVIBO, "abb71ca5fe1846f185cfbda554046cce")
    .replaces_endpoint(
        endpoint_id=1, device_type=zha.DeviceType.DIMMABLE_LIGHT
    )  # Was LEVEL_CONTROL_SWITCH
    .removes(Color.cluster_id, endpoint_id=1)
    .add_to_registry()
)
