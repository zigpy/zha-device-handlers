"""VZM36 Canopy Module."""

from zigpy.profiles import zha
from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.inovelli import (
    INOVELLI_AUTOMATION_TRIGGERS,
    InovelliVZM36FanCluster,
    InovelliVZM36LightCluster,
)

(
    QuirkBuilder("Inovelli", "VZM36")
    .replaces_endpoint(1, device_type=zha.DeviceType.DIMMABLE_LIGHT)
    .replaces(InovelliVZM36LightCluster)
    .replaces(InovelliVZM36FanCluster, endpoint_id=2)
    .device_automation_triggers(INOVELLI_AUTOMATION_TRIGGERS)
    .add_to_registry()
)
