"""Device handler for Terncy knob smart dimmer."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks import DoublingPowerConfigurationCluster
from zhaquirks.terncy import BUTTON_TRIGGERS, KNOB_TRIGGERS

(
    QuirkBuilder("Xiaoyan", "TERNCY-SD01")
    .applies_to(None, "TERNCY-SD01")
    .replaces(DoublingPowerConfigurationCluster, endpoint_id=1)
    .device_automation_triggers({**BUTTON_TRIGGERS, **KNOB_TRIGGERS})
    .add_to_registry()
)
